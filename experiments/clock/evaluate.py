"""Stockfish evals of the position after the 20th move, for the online game-sides without Lichess evals.

Reads data/clock/online/. Writes data/clock/stockfish/<chunk>.parquet: key, color, cp (centipawns, the side's
view; mates as in chesslab.games). Stockfish 19, 3,000 nodes, 1 thread, hash cleared for every position."""
from multiprocessing import Pool

import chess
import pandas as pd

from chesslab import DATA
from chesslab.engine import Stockfish
from chesslab.games import MATE

IN = DATA / "clock"


def side_cp(engine, fen, key, color):
    """The side's eval after its 20th move: minus the side to move's, or mate (the side has just mated) or 0."""
    board = chess.Board(fen)
    if board.is_game_over():
        return MATE if board.is_checkmate() else 0
    return -engine.analyse(board, nodes=3000, game=(key, color))[0][1]


def evaluate(path):
    out = IN / "stockfish" / path.name
    if not out.exists():
        sides = pd.read_parquet(path, columns=["key", "color", "fen"]).dropna(subset=["fen"])
        with Stockfish(hash_mb=16) as engine:
            sides["cp"] = [side_cp(engine, fen, key, color) for key, color, fen in sides.itertuples(index=False)]
        part = out.with_suffix(".part")
        sides.drop(columns="fen").to_parquet(part, index=False)
        part.rename(out)
    return path.stem


if __name__ == "__main__":
    (IN / "stockfish").mkdir(exist_ok=True)
    with Pool(12) as pool:
        for name in pool.imap_unordered(evaluate, sorted((IN / "online").glob("*.parquet"))):
            print(name, flush=True)
