"""Game-sides at the 20th move: over-the-board classical games and Lichess blitz and rapid games.

Reads the broadcast and Lichess files of data/. Writes, one file per input file, to data/clock/:
  otb/<month>.parquet       one row per side of a classical game that passes the sample rules (README, Method)
  openings/<month>.parquet  the first 40 plies of every over-the-board game, for the book depth
  online/<chunk>.parquet    one row per side of a blitz or rapid game that passes the sample rules, with
                            the position after the side's 20th move if the game has no Lichess evals"""
import re
from multiprocessing import Pool

import chess
import numpy as np
import pandas as pd

from chesslab import DATA, games, samples
from chesslab.games import win_chance

OUT = DATA / "clock"
C = 20  # the checkpoint: the side's 20th move
INCREMENTS = np.array([0, 5, 10, 15, 20, 30, 60])
ABORTED = {"Abandoned", "Rules infraction", "Unterminated"}


def replay(sans):
    """Legal moves before each of the first 40 plies; non-pawn material and FEN after plies 38 and 39."""
    board, legal, after = chess.Board(), [], {}
    for ply, san in enumerate(sans[:2 * C]):
        legal.append(board.legal_moves.count())
        board.push_san(san)
        if ply >= 2 * C - 2:
            pieces = 3 * chess.popcount(board.knights | board.bishops) + 5 * chess.popcount(board.rooks)
            after[ply] = (pieces + 9 * chess.popcount(board.queens), board.fen())
    return np.array(legal), after


def outcome_class(cp):
    """1 winning (at least +3 pawns), -1 losing (at most -3 pawns), else 0."""
    return (cp >= 300).astype(int) - (cp <= -300)


def sides(game, base, inc, elos):
    """The sides of a game that reach the opponent's 20th move and pass the sample rules."""
    n = len(game.sans)
    if n < 2 * C:
        return []
    try:
        legal, after = replay(game.sans)
    except ValueError:
        return []
    clock = np.array(game.clocks, float)
    ev = np.array([20] + game.evals, float)  # White's view before each ply and after the last; the start is +20 cp
    budget = base + 40 * inc
    marks = np.cumsum([("x" in san) + (san[-1] in "+#") for san in game.sans[:2 * C]])
    rows = []
    for color in (0, 1):
        ply, opponent_ply = 2 * (C - 1) + color, 2 * (C - 1) + 1 - color
        if n < ply + 2:
            continue
        own = np.arange(color, n, 2)
        early, late = own[:C], own[C:]
        clock_left = (clock[ply] + (40 - C) * inc) / budget
        opponent_clock_left = (clock[opponent_ply] + (40 - C) * inc) / budget
        if not (np.isfinite(clock[early]).all() and elos[0] and elos[1] and 0 <= clock_left <= 1.05
                and 0 <= opponent_clock_left <= 1.05 and clock[color] >= 0.6 * base + inc - 1):
            continue
        sign = 1 - 2 * color
        chance = win_chance(sign * ev)
        change = chance[1:] - chance[:-1]  # change of the side's win chance at each ply
        loss = np.maximum(0, -change)
        swing = np.abs(change[:ply + 1])
        before, after_move = sign * ev[late], sign * ev[late + 1]
        known = np.isfinite(before) & np.isfinite(after_move)
        rows.append({
            "color": color, "elo": elos[color], "opponent_elo": elos[1 - color],
            "score": game.result if color == 0 else 1 - game.result,
            "base": base, "increment": inc, "budget": budget,
            "clock_left": clock_left, "opponent_clock_left": opponent_clock_left,
            "lost_before_start": (base + inc - clock[color]) / budget,
            "minutes_used": (base + C * inc - clock[ply]) / 60,
            "early_error": np.nansum(loss[early]), "early_evals": np.isfinite(loss[early]).sum(),
            "error": np.nansum(loss[own]), "opponent_error": np.nansum(np.maximum(0, change[1 - color::2])),
            "evals": np.isfinite(ev[1:]).mean(), "win_chance": chance[ply + 1],
            "volatility": swing[np.isfinite(swing)].mean() if np.isfinite(swing).any() else np.nan,
            "legal_moves": legal[early].mean(), "captures_checks": marks[ply],
            "material": after[ply][0], "fen": after[ply][1],
            "time_trouble": bool((clock[late - 2] < 0.10 * budget).any()),
            "result_changing_error": bool((outcome_class(after_move[known]) < outcome_class(before[known])).any())})
    return rows


def max_gain(clocks):
    """Largest clock gain of White from one move to the next before move 40, at most 65 s: the increment
    minus the time of the fastest move."""
    gains = np.diff(np.array(clocks[0:78:2], float))
    gains = gains[gains <= 65]  # unknown gains drop out here too
    return gains.max() if gains.size else np.nan


def snap(gain):
    """The smallest usual increment that the gain reaches, with 1.5 s tolerance."""
    return int(INCREMENTS[INCREMENTS >= gain - 1.5][0]) if gain - 1.5 <= 60 else 60


def base_time(clocks, inc):
    """First clock of either side minus the increment, rounded to 5 minutes (from 30 minutes) or to 1 minute."""
    first = np.array(clocks[:2], float)
    if not np.isfinite(first).any():
        return np.nan
    base = np.nanmax(first) - inc
    step = 300 if base >= 1800 else 60
    return round(base / step) * step


def extra_time(clocks, inc):
    """1 if a clock jumps by more than the increment plus 5 minutes at move 41 (time added at move 40), 0 if not,
    NaN if unknown."""
    jumps = [clocks[i] - clocks[i - 2] for i in (80, 81) if i < len(clocks) and None not in (clocks[i], clocks[i - 2])]
    return float(any(j > inc + 300 for j in jumps)) if jumps else np.nan


def well_recorded(game):
    """Clocks and evals on at least 90% of plies, and clocks to the second (not only whole minutes)."""
    clock = np.array(game.clocks, float)
    known = clock[np.isfinite(clock)]
    return (np.isfinite(clock).mean() >= 0.9 and known.size > 0 and (known % 60 != 0).mean() > 0.2
            and np.mean([v is not None for v in game.evals]) >= 0.9)


def otb(path):
    """Classical sides and openings of one broadcast month. Relay clocks are noisy and TimeControl headers are free
    text, so the base, increment and time added at move 40 are set per event (5 or more well-recorded games)."""
    month = re.search(r"\d{4}-\d{2}", path.name).group()
    openings, classical = [], []
    for g in samples.otb_file(path):
        openings.append((g.key, g.headers.get("Date", ""), g.headers.get("Round", ""), g.white_fide, g.black_fide,
                         " ".join(g.sans[:2 * C])))
        if games.otb_speed(g.clocks) == "classical" and well_recorded(g):
            classical.append(g)
    events = pd.DataFrame({"event": [(g.headers.get("BroadcastName") or g.headers.get("Event", ""))[:100]
                                     for g in classical], "gain": [max_gain(g.clocks) for g in classical]})
    by = events.groupby("event")
    size = by.gain.transform("size")
    gain = events.gain.where(size < 5, by.gain.transform(lambda s: s.quantile(0.8)).fillna(events.gain))
    events["inc"] = [snap(x) if np.isfinite(x) else 0 for x in gain]
    events["base"] = [base_time(g.clocks, inc) for g, inc in zip(classical, events.inc)]
    events["extra"] = [extra_time(g.clocks, inc) for g, inc in zip(classical, events.inc)]
    by = events.groupby("event")
    usual = by.base.transform(lambda s: s.mode().iloc[0] if s.notna().any() else 0)
    events["base"] = events.base.where(size < 5, usual)
    share = by.extra.transform("mean")
    events["extra"] = (share > 0.5).astype("boolean").mask(share.isna())
    rows = []
    for g, e in zip(classical, events.itertuples()):
        if not e.base > 0 or e.base + 40 * e.inc < 3600:
            continue
        round_ = re.match(r"\s*(\d+)", g.headers.get("Round", ""))
        players = (g.white_fide, g.black_fide)
        for row in sides(g, int(e.base), e.inc, (g.white_elo, g.black_elo)):
            if players[row["color"]]:
                del row["fen"]
                rows.append(dict(key=g.key, month=month, event=e.event, round=int(round_.group(1)) if round_ else -1,
                                 extra_time=e.extra, player=players[row["color"]], **row))
    columns = ["key", "date", "round", "white_fide", "black_fide", "moves"]
    return {"openings": pd.DataFrame(openings, columns=columns), "otb": pd.DataFrame(rows)}


def online(path):
    """Blitz and rapid sides of one Lichess byte range. Games with a berserk (a side starts with less than 60% of
    the base) or that were aborted are left out."""
    rows = []
    for g in samples.lichess(path):
        h = g.headers
        speed = games.lichess_speed(h["TimeControl"])
        if speed not in ("blitz", "rapid") or h.get("Termination") in ABORTED:
            continue
        base, inc = (int(x) for x in h["TimeControl"].split("+"))
        if any(c is not None and c < 0.6 * base + inc for c in g.clocks[:2]):
            continue
        elos = [elo if elo and elo < 4000 else None for elo in (g.white_elo, g.black_elo)]
        hour = h.get("UTCTime", "")[:2]
        for row in sides(g, base, inc, elos):
            if row["evals"] >= 0.95:
                row["fen"] = None
            rows.append(dict(key=h["Site"][-8:], speed=speed, player=h["White" if row["color"] == 0 else "Black"],
                             hour=int(hour) // 6 if hour.isdigit() else -1,
                             lost_on_time=h.get("Termination") == "Time forfeit" and row["score"] == 0, **row))
    return {"online": pd.DataFrame(rows)}


def run(job):
    work, path = job
    name = re.search(r"\d{4}-\d{2}", path.name).group() if work is otb else path.stem
    done = OUT / work.__name__ / f"{name}.parquet"
    if not done.exists():
        for folder, table in work(path).items():  # the work's own folder last: it marks the file as done
            part = OUT / folder / f"{name}.part"
            table.to_parquet(part, index=False)
            part.rename(part.with_suffix(".parquet"))
    return name


if __name__ == "__main__":
    for folder in ("otb", "openings", "online"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    jobs = [(otb, p) for p in samples.broadcast_files()] + [(online, p) for p in samples.lichess_files()]
    with Pool(8) as pool:
        for name in pool.imap_unordered(run, sorted(jobs, key=lambda j: -j[1].stat().st_size)):
            print(name, flush=True)
