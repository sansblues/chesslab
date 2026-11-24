"""Stockfish 19 with one thread and a fixed number of nodes, so that a run can be repeated."""
import chess
import chess.engine

from chesslab.data import STOCKFISH
from chesslab.games import MATE


class Stockfish:
    """with Stockfish() as engine: engine.analyse(board, nodes=30_000, multipv=2)"""

    def __init__(self, hash_mb: int = 16):
        self.engine = chess.engine.SimpleEngine.popen_uci(str(STOCKFISH))
        self.engine.configure({"Threads": 1, "Hash": hash_mb})

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.engine.quit()

    def analyse(self, board: chess.Board, nodes: int | None = None, depth: int | None = None,
                multipv: int = 1, game: object = None) -> list[tuple[chess.Move, int]]:
        """The best moves, best first, each with its score for the side to move in centipawns
        (mates: see games.MATE). A new game clears the hash table: give each game its own key."""
        infos = self.engine.analyse(board, chess.engine.Limit(nodes=nodes, depth=depth), multipv=multipv, game=game)
        return [(info["pv"][0], info["score"].pov(board.turn).score(mate_score=MATE)) for info in infos if "pv" in info]
