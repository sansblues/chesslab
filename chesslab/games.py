"""Read Lichess PGN databases as a stream of games, with the clock and eval of every ply."""
import hashlib
import io
import itertools
import re
from dataclasses import dataclass

import numpy as np
import zstandard

MATE = 32000  # eval of mate in n: MATE - n if White mates, -(MATE - n) if Black mates

_HEADER = re.compile(r'^\[(\w+) "(.*)"\]\s*$')
_TOKEN = re.compile(r"\{[^}]*\}|\(|\)|\$\d+|\d+\.+|1-0|0-1|1/2-1/2|\*|[^\s{}()]+")
_CLOCK = re.compile(r"%clk (\d+):(\d+):(\d+(?:\.\d+)?)")
_EVAL = re.compile(r"%eval (#?)(-?[\d.]+)")
_ANNOTATION = re.compile(r"[?!]+$")
_RESULT = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


@dataclass(slots=True)
class Game:
    headers: dict[str, str]
    sans: list[str]  # main line
    clocks: list[float | None]  # mover's clock after each ply, in seconds
    evals: list[int | None]  # eval after each ply, White's view, in centipawns (mates: see MATE)

    @property
    def result(self) -> float | None:
        """White's score: 1, 0.5 or 0. None if the game has no result."""
        return _RESULT.get(self.headers.get("Result"))

    @property
    def white_elo(self) -> int | None:
        return _positive(self.headers.get("WhiteElo"))

    @property
    def black_elo(self) -> int | None:
        return _positive(self.headers.get("BlackElo"))

    @property
    def white_fide(self) -> int | None:
        return _positive(self.headers.get("WhiteFideId"))

    @property
    def black_fide(self) -> int | None:
        return _positive(self.headers.get("BlackFideId"))

    @property
    def key(self) -> str:
        """Same players, same moves: same game. Several broadcasts can relay one game."""
        text = "|".join([self.headers.get("White", ""), self.headers.get("Black", "")] + self.sans)
        return hashlib.md5(text.encode()).hexdigest()[:16]


def read(path, partial=False):
    """Games of a .pgn.zst file. partial: the file is a byte range cut from one;
    the games cut at either end are dropped."""
    for headers, movetext in _split(_lines(path, partial), drop_last=partial):
        yield Game(headers, *_moves(movetext))


def win_chance(cp):
    """Lichess win chance, 0..1, of the side whose eval is cp centipawns, clipped to ±1000 (mates count as
    ±1000). Works on numbers and arrays."""
    return 1 / (1 + np.exp(-0.00368208 * np.clip(cp, -1000, 1000)))


def lichess_speed(time_control: str | None) -> str:
    """Speed of a Lichess TimeControl header such as "180+2", from base + 40 × increment."""
    try:
        base, inc = (int(x) for x in time_control.split("+"))
    except (AttributeError, ValueError):
        return "unknown"
    est = base + 40 * inc
    for limit, speed in ((30, "ultrabullet"), (180, "bullet"), (480, "blitz"), (1500, "rapid")):
        if est < limit:
            return speed
    return "classical"


def otb_clock(clocks: list[float | None]) -> tuple[float | None, float | None]:
    """Base and increment of an over-the-board game, inferred from its clocks (broadcast
    TimeControl headers are free text). Base: White's clock after move 1. Increment: the
    largest clock gain between White's moves before move 40 (the move-40 addition comes
    later), at most 60 s."""
    white = clocks[0:78:2]
    if not white or white[0] is None:
        return None, None
    gains = [b - a for a, b in itertools.pairwise(white) if a is not None and b is not None]
    return white[0], min(max([0.0] + gains), 60.0)


def otb_speed(clocks: list[float | None]) -> str:
    """FIDE speed from base + 60 × increment: classical from 60 min, rapid from 10 min."""
    base, inc = otb_clock(clocks)
    if base is None:
        return "unknown"
    est = base + 60 * inc
    return "classical" if est >= 3600 else "rapid" if est >= 600 else "blitz"


def _positive(text: str | None) -> int | None:
    try:
        value = int(text)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _lines(path, partial):
    with open(path, "rb") as f:
        src = f
        if partial:  # start at the first zstd frame that decodes
            data = f.read()
            start = data.find(_ZSTD_MAGIC)
            while start != -1:
                try:
                    zstandard.ZstdDecompressor().decompressobj().decompress(data[start:start + (1 << 20)])
                    break
                except zstandard.ZstdError:
                    start = data.find(_ZSTD_MAGIC, start + 1)
            src = io.BytesIO(data[start:])
        reader = zstandard.ZstdDecompressor().stream_reader(src, read_across_frames=True)
        try:
            yield from io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
        except zstandard.ZstdError:  # the cut end of a byte range
            return


def _split(lines, drop_last):
    """(headers, movetext) of every game that starts with an Event header."""
    headers, moves, state = {}, [], "before"
    for line in lines:
        if line.startswith("["):
            m = _HEADER.match(line)
            if not m:
                continue
            if m.group(1) == "Event":
                if state == "moves":
                    yield headers, " ".join(moves)
                headers, moves, state = {}, [], "headers"
            if state != "before":
                headers[m.group(1)] = m.group(2)
        elif state != "before" and line.strip():
            state = "moves"
            moves.append(line.strip())
    if state == "moves" and not drop_last:
        yield headers, " ".join(moves)


def _moves(movetext):
    """Main-line SANs, and the clock and eval in the comment after each move."""
    sans, clocks, evals = [], [], []
    depth = 0
    for token in _TOKEN.findall(movetext):
        c = token[0]
        if c == "{":
            if depth == 0 and sans:
                if m := _CLOCK.search(token):
                    clocks[-1] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
                if m := _EVAL.search(token):
                    evals[-1] = _eval(m.group(1) == "#", m.group(2), len(sans) - 1)
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif not (depth or c == "$" or c.isdigit() or token == "*"):
            sans.append(_ANNOTATION.sub("", token))
            clocks.append(None)
            evals.append(None)
    return sans, clocks, evals


def _eval(mate, text, ply):
    if not mate:
        return round(float(text) * 100)
    n = int(float(text))
    if n == 0:  # the side to move is mated; Lichess writes "#0" or "#-0", so the sign is lost
        return MATE if ply % 2 == 0 else -MATE
    return MATE - n if n > 0 else -MATE - n
