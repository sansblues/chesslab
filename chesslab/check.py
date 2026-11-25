"""Check the core against known counts (make check, about 7 minutes).
The numbers are of the data in data/; see chesslab.data."""
import collections
import random
import sys
from multiprocessing import Pool

import chess

from chesslab import games, samples, tablebase
from chesslab.engine import Stockfish

failed = 0


def report(name, expected, got):
    global failed
    failed += expected != got
    print(f"{'ok' if expected == got else 'FAIL':4}  {name:46} expected {_show(expected):>14}  got {_show(got):>14}",
          flush=True)


def _show(value):
    return f"{value:,}" if isinstance(value, int) else str(value)


def lichess_counts(path):
    """Games by speed, and final mates whose eval has the wrong sign."""
    counts = collections.Counter()
    for game in samples.lichess(path):
        counts[games.lichess_speed(game.headers["TimeControl"])] += 1
        if game.sans[-1].endswith("#") and game.evals[-1] is not None:
            counts["wrong mate sign"] += game.evals[-1] != (games.MATE if len(game.sans) % 2 else -games.MATE)
    return counts


def lichess():
    counts = collections.Counter()
    with Pool(8) as pool:
        for c in pool.imap_unordered(lichess_counts, samples.lichess_files()):
            counts.update(c)
    report("Lichess sample: games", 3_178_824, sum(counts[s] for s in samples.LICHESS_SPEEDS))
    for speed, n in (("bullet", 1_124_803), ("blitz", 1_473_898), ("rapid", 559_629), ("classical", 20_494)):
        report(f"  {speed}", n, counts[speed])
    report("  final mates with a wrong eval sign", 0, counts["wrong mate sign"])


def otb():
    counts = collections.Counter(games.otb_speed(game.clocks) for game in samples.otb())
    report("OTB games", 743_828, sum(counts.values()))
    for speed, n in (("blitz", 82_043), ("rapid", 134_569), ("classical", 488_856), ("unknown", 38_360)):
        report(f"  {speed}", n, counts[speed])


def fide():
    for month, n in (("jul24", 468_009), ("jul25", 510_088), ("jul26", 559_303), ("nov26", 573_475)):
        report(f"FIDE list {month}: players", n, len(samples.fide(month)))


def random_krppvkr(rng):
    while True:
        board = chess.Board(None)
        squares = rng.sample(range(8, 56), 2) + [rng.randrange(64) for _ in range(4)]
        if len(set(squares)) < 6:
            continue
        for square, symbol in zip(squares, "PPKRkr"):
            board.set_piece_at(square, chess.Piece.from_symbol(symbol))
        board.turn = rng.random() < 0.5
        if board.is_valid():
            return board


def fathom():
    rng = random.Random(11)
    boards = [random_krppvkr(rng) for _ in range(20_000)]
    disagree = sum(tablebase.fathom_wdl(b) != tablebase.syzygy().probe_wdl(b) for b in boards)
    report("Fathom vs python-chess: KRPPvKR disagreements", 0, disagree)
    codes = tablebase.enumerate_wdl("KPvK")  # published: syzygy-tables.info
    report("Fathom KPvK, White to move: draws, wins", (19_184, 62_480),
           (int((codes[0] == 2).sum()), int((codes[0] == 4).sum())))
    report("Fathom KPvK, Black to move: losses, draws", (48_802, 35_210),
           (int((codes[1] == 0).sum()), int((codes[1] == 2).sum())))


def stockfish():
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    with Stockfish() as engine:
        move, score = engine.analyse(board, nodes=10_000)[0]
    report("Stockfish: back-rank mate in 1", ("a1a8", games.MATE - 1), (move.uci(), score))


if __name__ == "__main__":
    for step in (stockfish, fathom, fide, lichess, otb):
        step()
    sys.exit(failed > 0)
