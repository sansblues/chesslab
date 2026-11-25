"""Read the broadcast games of Sep 2026. Write one row per player-game with rating, mistakes and loss
(data/cheating/player_games.csv; counts in results/sample.csv), and the Stockfish view of every position
of 420 classical games (data/cheating/positions.csv; about 8 min, kept if present)."""
import math
import random
from multiprocessing import Pool
from pathlib import Path

import chess
import pandas as pd

from chesslab import DATA, games
from chesslab.engine import Stockfish

SOURCE = DATA / "broadcast" / "lichess_db_broadcast_2026-09.pgn.zst"
OUT = DATA / "cheating"
SAMPLE_PER_BAND = 60
FIRST_PLY = 16  # the first 8 moves of each side are not judged


def win(cp):
    """Lichess win% of the side whose eval is cp, clipped to ±1000 (mates count as ±1000)."""
    return 100 / (1 + math.exp(-0.00368208 * max(-1000, min(1000, cp))))


def speed(clock):
    """The research's rule, from White's first clock."""
    if not clock:
        return "unknown"
    return "classical" if clock >= 3000 else "rapid" if clock >= 540 else "blitz"


def kept(game):
    """Both ratings 1000-2900, at least 30 plies, at most 2 plies without an eval."""
    return (all(e and 1000 <= e <= 2900 for e in (game.white_elo, game.black_elo))
            and len(game.sans) >= 30 and game.evals.count(None) <= 2)


def player_games(game):
    """Both sides of a game, each with at least 10 judged moves. A move in a decided position
    (win% before ≤ 3 or ≥ 97) does not count; a mistake loses at least 10 win%."""
    elos = game.white_elo, game.black_elo
    evals = [20] + game.evals  # eval before each ply; the start position: +0.20 assumed
    rows = []
    for side, sign in ((0, 1), (1, -1)):
        before, after = evals[FIRST_PLY + side:-1:2], evals[FIRST_PLY + side + 1::2]
        moves = [(win(sign * a), win(sign * b)) for a, b in zip(before, after) if a is not None and b is not None]
        if len(moves) < 10:
            continue
        losses = [a - b for a, b in moves if 3 < a < 97]
        player = (game.black_fide, game.headers.get("Black")) if side else (game.white_fide, game.headers.get("White"))
        rows.append({"speed": speed(game.clocks[0]), "elo": elos[side], "opponent_elo": elos[1 - side],
                         "player": player[0] or player[1], "moves": len(losses),
                         "mistakes": sum(x >= 10 for x in losses), "loss": sum(max(x, 0) for x in losses)})
    return rows


def sample():
    """The research's draw: classical games with clocks and evals, average rating 1400-2799,
    rating gap ≤ 300; 60 games per 200-point band of the average, seed 1."""
    bands = {}
    for game in games.read(SOURCE):
        elos = game.white_elo, game.black_elo
        clocks = [c for c in game.clocks if c is not None]
        if not (all(elos) and clocks and clocks[0] >= 3000 and any(e is not None for e in game.evals)):
            continue
        average = sum(elos) / 2
        if 1400 <= average < 2800 and abs(elos[0] - elos[1]) <= 300:
            bands.setdefault(average // 200, []).append((game.headers.get("GameURL"), *elos, game.sans))
    random.seed(1)
    chosen = []
    for band in sorted(bands):
        random.shuffle(bands[band])
        chosen += bands[band][:SAMPLE_PER_BAND]
    return chosen


def start_engine():
    global engine
    engine = Stockfish(hash_mb=64)


def analyse(game):
    """Win% of the best and the second-best move (mover's view), and whether the mover chose the best."""
    url, white_elo, black_elo, sans = game
    board, rows = chess.Board(), []
    for ply, san in enumerate(sans):
        move = board.parse_san(san)
        if ply >= FIRST_PLY:
            lines = engine.analyse(board, nodes=30_000, multipv=2, game=url)
            rows.append({"game": url, "ply": ply, "elo": black_elo if ply % 2 else white_elo,
                         "best": win(lines[0][1]), "second": win(lines[1][1]) if len(lines) > 1 else None,
                         "found": move == lines[0][0]})
        board.push(move)
    return rows


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    selected = [player_games(game) for game in games.read(SOURCE) if kept(game)]
    rows = [row for pair in selected for row in pair]
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "player_games.csv", index=False, float_format="%.6g")
    counts = {"games": len(selected), "player_games": len(table)} | table.speed.value_counts().to_dict()
    pd.DataFrame([counts]).to_csv(Path(__file__).parent / "results" / "sample.csv", index=False)
    print(counts)

    positions = OUT / "positions.csv"
    if not positions.exists():
        with Pool(10, initializer=start_engine) as pool:
            rows = [row for game in pool.imap(analyse, sample()) for row in game]
        pd.DataFrame(rows).to_csv(positions.with_suffix(".part"), index=False, float_format="%.6g")
        positions.with_suffix(".part").rename(positions)
    print(f"{len(pd.read_csv(positions))} positions analysed")
