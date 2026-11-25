"""Re-check, with a deeper Stockfish search, online resignations that the recorded eval calls not lost.

Reads data/decided/ (extract.py). Writes results/resignation_recheck.csv: 150 of these positions,
the first by the MD5 of the game URL, with the recorded and the Stockfish value for the resigner.
"""
import hashlib
from multiprocessing import Pool
from pathlib import Path

import chess
import pandas as pd

from chesslab import DATA
from chesslab.engine import Stockfish

RESULTS = Path(__file__).parent / "results"
SAMPLE = 150
NODES = 3_000_000


def search(item):
    fen, resigner = item
    board = chess.Board(fen)
    with Stockfish(hash_mb=64) as engine:
        [(_, score)] = engine.analyse(board, nodes=NODES)
    return score if board.turn == resigner else -score


if __name__ == "__main__":
    g = pd.concat([pd.read_parquet(p) for p in sorted((DATA / "decided").glob("lichess_*.games.parquet"))],
                  ignore_index=True)
    g = g[(g.end == "resign") & g.final_fen.notna() & ~g.final_tablebase.astype(bool)].copy()
    g["recorded"] = g.final_value.where(g.result == 0, -g.final_value)
    g = g[g.recorded > -300]
    g = g.loc[g.url.map(lambda u: hashlib.md5(u.encode()).hexdigest()).sort_values().index[:SAMPLE]]
    with Pool(12) as pool:
        g["stockfish"] = pool.map(search, zip(g.final_fen, g.result == 0))
    g[["url", "speed", "recorded", "stockfish"]].to_csv(RESULTS / "resignation_recheck.csv", index=False,
                                                       float_format="%.6g")
