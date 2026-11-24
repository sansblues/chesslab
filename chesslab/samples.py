"""The data samples shared by the experiments."""
import itertools
import re
import zipfile

import chess
import pandas as pd

from chesslab import DATA, games

LICHESS = DATA / "lichess" / "2026-10"
BROADCAST = DATA / "broadcast"
FIDE = DATA / "fide"
LICHESS_SPEEDS = ("bullet", "blitz", "rapid", "classical")

# Relays of online or engine events. The Site of an over-the-board relay is often the broadcast URL.
ONLINE = re.compile(r"online|titled tuesday|(?<![a-z])chess\.com|lichess\.org/(?!broadcast)|armageddon|freestyle|"
                    r"chess960|fischer random|\b960\b|tcec|\bccc\b|engine|computer", re.IGNORECASE)


def lichess_files():
    """48 byte ranges of the Lichess database of rated games, Oct 2026, evenly spaced over the
    file: a sample spread over the whole month."""
    return sorted(LICHESS.glob("chunk_*.bin"))


def lichess(path):
    """Games of one byte range: standard chess, bullet to classical, with a result and a move."""
    for game in games.read(path, partial=True):
        if _complete(game) and games.lichess_speed(game.headers.get("TimeControl")) in LICHESS_SPEEDS:
            yield game


def broadcast_files():
    """Lichess broadcasts (relays of over-the-board events), Jul 2024 - Oct 2026, one file a month."""
    return sorted(BROADCAST.glob("lichess_db_broadcast_*.pgn.zst"))


def otb():
    """Over-the-board games: broadcast games of standard chess with a result and a move, not from
    online or engine events. Each game once: its first relay, in file order. The moves are not
    replayed: a few games have an illegal move."""
    seen = set()
    for path in broadcast_files():
        for game in otb_file(path):
            if game.key not in seen:
                seen.add(game.key)
                yield game


def otb_file(path):
    """The over-the-board games of one broadcast file, for work in parallel. A game relayed by
    several broadcasts comes once per relay: keep the first by Game.key, in file order."""
    for game in games.read(path):
        if _complete(game) and not online(game):
            yield game


def online(game) -> bool:
    """A relay of an online or engine event, by its name and site, or by a rating above 2900."""
    h = game.headers
    text = (h.get("BroadcastName") or h.get("Event", ""))[:80] + " @" + h.get("Site", "")[:40]
    return bool(ONLINE.search(text)) or max(game.white_elo or 0, game.black_elo or 0) > 2900


def fide(month: str) -> pd.DataFrame:
    """FIDE standard rating list of a month such as "jul25", one row per player."""
    with zipfile.ZipFile(FIDE / f"standard_{month}frl.zip") as z:
        lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    header = lines[0]
    columns = {"id": "ID Number", "name": "Name", "federation": "Fed", "sex": "Sex", "title": "Tit",
               "_": "WTit", "rating": month.upper(), "games": "Gms", "k": " K ", "birth_year": "B-day", "flag": "Flag"}
    starts = [header.index(c) + (c == " K ") for c in columns.values()] + [None]
    table = pd.DataFrame([[line[a:b].strip() for a, b in itertools.pairwise(starts)] for line in lines[1:]],
                         columns=list(columns)).drop(columns="_")
    for c in ("id", "rating", "games", "k", "birth_year"):
        table[c] = pd.to_numeric(table[c], errors="coerce").astype("Int64")
    return table.dropna(subset=["id", "rating"]).reset_index(drop=True)


def _complete(game) -> bool:
    """Standard chess with a result and at least one move. A game recorded from another start
    position is dropped: most are Chess960; a few are relays with a wrong FEN."""
    h = game.headers
    return (h.get("Variant", "Standard") == "Standard" and h.get("FEN", chess.STARTING_FEN) == chess.STARTING_FEN
            and game.result is not None and bool(game.sans))
