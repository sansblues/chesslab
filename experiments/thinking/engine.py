"""Value of thinking per position: Stockfish 19, one thread, Hash 16, a new game per position.
Reads data/thinking/positions.parquet. Writes data/thinking/stockfish/chunk_*.parquet: per unique FEN
the best move of a depth-4 and of a depth-8 search, and the scores (centipawns, side to move) of the
best move and of both shallow moves, from a 30,000-node MultiPV-2 search; a shallow move outside its
top two gets a 7,500-node search restricted to the shallow moves. About 5 hours on 12 cores; FENs in
existing chunks are skipped."""
from multiprocessing import Pool

import chess
import chess.engine
import pandas as pd

from chesslab import DATA
from chesslab.engine import Stockfish
from chesslab.games import MATE

OUT = DATA / "thinking" / "stockfish"
COLUMNS = ["fen", "best_move", "depth4_move", "depth8_move", "best_cp", "depth4_cp", "depth8_cp"]
NODES = 30_000
CHUNK = 5000
engine = None


def start():
    global engine
    engine = Stockfish(hash_mb=16)


def analyse(fen):
    board = chess.Board(fen)
    game = object()  # one game per position: the hash is cleared, then kept over the three searches
    depth4 = engine.analyse(board, depth=4, game=game)[0][0].uci()
    depth8 = engine.analyse(board, depth=8, game=game)[0][0].uci()
    deep = engine.analyse(board, nodes=NODES, multipv=2, game=game)
    scores = {move.uci(): cp for move, cp in deep}
    rest = [chess.Move.from_uci(m) for m in {depth4, depth8} - scores.keys()]
    if rest:  # the core wrapper has no root_moves
        infos = engine.engine.analyse(board, chess.engine.Limit(nodes=NODES // 4), multipv=len(rest),
                                      root_moves=rest, game=game)
        scores |= {i["pv"][0].uci(): i["score"].pov(board.turn).score(mate_score=MATE) for i in infos}
    best = deep[0][0].uci()
    return fen, best, depth4, depth8, scores[best], scores[depth4], scores[depth8]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    chunks = sorted(OUT.glob("chunk_*.parquet"))
    done = set(pd.concat([pd.read_parquet(f, columns=["fen"]) for f in chunks]).fen) if chunks else set()
    fens = pd.read_parquet(DATA / "thinking" / "positions.parquet", columns=["fen"]).fen.unique()
    todo = [fen for fen in fens if fen not in done]
    print("unique", len(fens), "to analyse", len(todo), flush=True)
    with Pool(12, initializer=start) as pool:
        for i in range(0, len(todo), CHUNK):
            rows = pool.map(analyse, todo[i:i + CHUNK], chunksize=20)
            path = OUT / f"chunk_{len(chunks) + i // CHUNK:04d}.parquet"
            pd.DataFrame(rows, columns=COLUMNS).to_parquet(path.with_suffix(".part"), index=False)
            path.with_suffix(".part").rename(path)
            print(path.name, i + len(rows), "/", len(todo), flush=True)


if __name__ == "__main__":
    main()
