"""Replay the games that have an engine eval on almost every ply.

Reads the Lichess sample and the over-the-board broadcasts. Writes, per input file,
data/decided/<file>.games.parquet (one row per game) and data/decided/<file>.plies.parquet
(one row per ply of the replayed games: online games, and over-the-board classical games).
"""
from array import array
from multiprocessing import Pool

import chess
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from chesslab import DATA, games, samples, tablebase

OUT = DATA / "decided"


def has_eval(game):
    n = len(game.sans)
    return n >= 4 and sum(e is not None for e in game.evals) >= 0.95 * (n - 1)


def end(game):
    """mate, resign, flag, draw or abandon."""
    termination = game.headers.get("Termination")
    decisive = game.result != 0.5
    if termination in ("Abandoned", "Rules infraction"):
        return "abandon"
    if termination == "Time forfeit":
        return "flag" if decisive else "draw"
    if termination == "Insufficient material":
        return "draw"
    if game.sans[-1].endswith("#"):
        return "mate"
    return "resign" if decisive else "draw"


def budget(game, online):
    """Base time and the estimated game duration base + 40 × increment, in seconds."""
    if online:
        base, increment = (int(x) for x in game.headers["TimeControl"].split("+"))
    else:
        base, increment = games.otb_clock(game.clocks)
        base, increment = int(base), round(increment)
    return base, max(1, base + 40 * increment)


def last_clock(clocks, side):
    return next((c for c in reversed(clocks[side::2]) if c is not None), None)


def replay(game, online, plies):
    """Append the plies of a game to the columns in plies; return its final board.
    value: White's value after the move, in centipawns: the Syzygy value (±1000 or 0) at six pieces
    or fewer, else the eval (a mate: ±MATE). clock: the mover's clock before the move, as a fraction
    of the budget. pieces, material: before the move; material is the non-pawn material of both
    sides, in pawns."""
    base, total = budget(game, online)
    board = chess.Board()
    rows = []
    for k, san in enumerate(game.sans):
        pieces = chess.popcount(board.occupied)
        material = (3 * chess.popcount(board.knights | board.bishops) + 5 * chess.popcount(board.rooks)
                    + 9 * chess.popcount(board.queens))
        clock = game.clocks[k - 2] if k >= 2 else base or game.clocks[k]
        board.push_san(san)
        value = game.evals[k]
        if san.endswith("#"):  # the eval after the mating move can be missing
            value = games.MATE if k % 2 == 0 else -games.MATE
        if chess.popcount(board.occupied) <= 6 and (wdl := tablebase.wdl(board)) is not None:
            value = 1000 * (wdl if board.turn == chess.WHITE else -wdl)
        rows.append((k, np.nan if value is None else value, np.nan if clock is None else clock / total, pieces,
                     material))
    for column, values in zip(plies[1:], zip(*rows)):
        column.extend(values)
    return board


def process(path):
    online = path.parent.name != "broadcast"
    name = f"lichess_{path.stem}" if online else path.name.split(".")[0].removeprefix("lichess_db_")
    out = OUT / f"{name}.games.parquet"
    if out.exists():
        return name
    rows = []
    plies = [array("i"), array("h"), array("f"), array("f"), array("b"), array("b")]
    for i, game in enumerate(samples.lichess(path) if online else samples.otb_file(path)):
        speed = games.lichess_speed(game.headers["TimeControl"]) if online else games.otb_speed(game.clocks)
        row = {"game": i, "speed": speed, "white_elo": game.white_elo, "black_elo": game.black_elo,
               "result": game.result, "end": end(game), "plies": len(game.sans), "has_eval": has_eval(game),
               "key": None if online else game.key, "url": None, "final_fen": None, "final_value": None,
               "final_tablebase": None, "white_clock": None, "black_clock": None}
        if row["has_eval"] and (online or speed == "classical"):
            try:
                board = replay(game, online, plies)
            except ValueError:  # an illegal move: drop the game
                continue
            plies[0].extend([i] * len(game.sans))
            row.update(url=game.headers.get("GameURL") or game.headers["Site"], final_fen=board.fen(),
                       final_value=plies[2][-1], final_tablebase=chess.popcount(board.occupied) <= 6
                       and tablebase.wdl(board) is not None,
                       white_clock=last_clock(game.clocks, 0), black_clock=last_clock(game.clocks, 1))
        rows.append(row)
    names = ["game", "ply", "value", "clock", "pieces", "material"]
    pq.write_table(pa.table({c: np.array(v) for c, v in zip(names, plies)}), OUT / f"{name}.plies.parquet")
    part = out.with_suffix(".part")
    pq.write_table(pa.Table.from_pylist(rows), part)
    part.rename(out)
    return name


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    paths = sorted(samples.lichess_files() + samples.broadcast_files(), key=lambda p: -p.stat().st_size)
    with Pool(12) as pool:
        for name in pool.imap_unordered(process, paths):
            print(name, flush=True)
