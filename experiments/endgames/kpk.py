"""KPvK: a short rule plus a few plies of calculation. Reads the KPvK tablebase (Fathom); writes
results/kpk_depth.csv: for each rule and search depth, the positions it gets wrong.

The rule judges the leaves of a full-width search of d plies (minimax, d = 0 is the rule alone). A
capture or promotion ends a line with its tablebase value. Positions: all legal KPvK positions,
pawn on files a-d (the others are their mirror images); White has the pawn."""
from collections import deque
from pathlib import Path
from typing import NamedTuple

import chess
import numpy as np
import pandas as pd
from endgame import distance, file, rank

from chesslab import tablebase

DEPTHS = range(41)


class Position(NamedTuple):
    king: int
    pawn: int
    black_king: int
    white_to_move: bool
    black_stuck: bool  # Black to move and has no legal move


def square(f, r):
    return (r - 1) * 8 + f - 1


def near(s):
    """The squares a king on s covers, and s."""
    return {square(f, r) for f in range(file(s) - 1, file(s) + 2) for r in range(rank(s) - 1, rank(s) + 2)
            if 1 <= f <= 8 and 1 <= r <= 8}


def rook_pawn(p):
    return file(p.pawn) == 1


def pawn_hangs(p):
    return not p.white_to_move and distance(p.black_king, p.pawn) == 1 and distance(p.king, p.pawn) > 1


def outside_square(p):
    """Rule of the square: the black king cannot catch the pawn (the kings' other moves ignored)."""
    moves = 8 - rank(p.pawn) - (rank(p.pawn) == 2)
    return distance(p.black_king, square(file(p.pawn), 8)) > moves + (not p.white_to_move)


def blocks_rook_pawn(p):
    """The white king stands in front of its own rook pawn."""
    return rook_pawn(p) and file(p.king) == 1 and rank(p.king) > rank(p.pawn)


def key_squares(p):
    """b7 and b8 for a rook pawn; else the three squares two ranks ahead of the pawn, from the
    5th rank also one rank ahead."""
    if rook_pawn(p):
        return {square(2, 7), square(2, 8)}
    ranks = [rank(p.pawn) + 2] if rank(p.pawn) <= 4 else [rank(p.pawn) + 1, rank(p.pawn) + 2]
    return {square(f, r) for f in range(file(p.pawn) - 1, file(p.pawn) + 2) for r in ranks if 1 <= f <= 8 and r <= 8}


def wins_key_square_race(p):
    white = min(distance(p.king, k) for k in key_squares(p))
    black = min(distance(p.black_king, k) for k in key_squares(p))
    return white <= black if p.white_to_move else white < black


def wins_corner_race(p):
    """Rook pawn: the white king reaches b7 or b8 before the black king reaches the corner."""
    corner = {square(f, r) for f in (1, 2, 3) for r in (7, 8)}
    blocked = near(p.king) | {square(2, rank(p.pawn) + 1)}  # and the square the pawn guards
    black = king_path(p.black_king, corner - blocked, blocked)
    white = min(distance(p.king, square(2, 7)), distance(p.king, square(2, 8)))
    return black > white + p.white_to_move


def king_path(start, targets, blocked):
    """Fewest king moves from start to a target, around the blocked squares; 99 if none."""
    steps, queue = {start: 0}, deque([start])
    while queue:
        s = queue.popleft()
        if s in targets:
            return steps[s]
        for t in near(s) - blocked - steps.keys():
            steps[t] = steps[s] + 1
            queue.append(t)
    return 99


def always_draw(p):
    return False


def textbook(p):
    """The rule of the square and the key squares."""
    return outside_square(p) or p.king in key_squares(p)


def sound(p):
    """Never a false win: no move for Black or a hanging pawn is a draw; the square and the key
    squares only where they hold for the rook pawn."""
    if p.black_stuck or pawn_hangs(p):
        return False
    return outside_square(p) and not blocks_rook_pawn(p) or not rook_pawn(p) and p.king in key_squares(p)


def accurate(p):
    """The most accurate short rule found: textbook plus the hanging pawn and two king races."""
    if pawn_hangs(p):
        return False
    if outside_square(p) and not blocks_rook_pawn(p):
        return True
    if rook_pawn(p):
        return wins_corner_race(p)
    return p.king in key_squares(p) or wins_key_square_race(p)


RULES = always_draw, textbook, accurate, sound


def graph():
    """Every legal position, its tablebase value, and its moves: child position or end value."""
    codes = tablebase.enumerate_wdl("KPvK")  # axes: side to move, king, pawn (a2..d7), black king
    legal = np.flatnonzero(codes.ravel() <= 4)
    number = np.full(codes.size, -1)
    number[legal] = np.arange(len(legal))
    positions, starts, children, ends = [], [], [], []
    for turn, king, pawn_index, black_king in zip(*np.unravel_index(legal, codes.shape)):
        pawn = 8 + pawn_index // 4 * 8 + pawn_index % 4
        board = chess.Board(None)
        for s, piece in ((king, "K"), (pawn, "P"), (black_king, "k")):
            board.set_piece_at(int(s), chess.Piece.from_symbol(piece))
        board.turn = bool(turn == 0)
        starts.append(len(children))
        moves = list(board.legal_moves)
        positions.append(Position(int(king), int(pawn), int(black_king), board.turn, not moves and not board.turn))
        if not moves:  # mate or stalemate
            children.append(-1)
            ends.append(board.is_checkmate())
        for move in moves:
            board.push(move)
            if move.promotion or len(board.piece_map()) < 3:  # the pawn queens or falls
                children.append(-1)
                ends.append(tablebase.wdl(board) == (1 if board.turn else -1))
            else:
                s = [board.king(chess.WHITE), board.pawns.bit_length() - 1, board.king(chess.BLACK)]
                if file(s[1]) > 4:
                    s = [x ^ 7 for x in s]
                children.append(number[np.ravel_multi_index(
                    (int(not board.turn), s[0], (rank(s[1]) - 2) * 4 + file(s[1]) - 1, s[2]), codes.shape)])
                ends.append(False)
            board.pop()
    truth = np.where(np.arange(2)[:, None, None, None] == 0, codes == 4, codes == 0).ravel()[legal]
    return positions, truth, np.array(starts), np.array(children), np.array(ends)


def depth_table():
    positions, truth, starts, children, ends = graph()
    white_to_move = np.array([p.white_to_move for p in positions])
    rows = []
    for rule in RULES:
        value = np.array([rule(p) for p in positions])
        for depth in DEPTHS:
            if depth:
                moves = np.where(children >= 0, value[children], ends)
                value = np.where(white_to_move, np.logical_or.reduceat(moves, starts),
                                 np.logical_and.reduceat(moves, starts))
            rows.append({"rule": rule.__name__, "depth": depth, "positions": len(positions),
                         "false_wins": int((value & ~truth).sum()), "false_draws": int((~value & truth).sum())})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    table = depth_table()
    table.to_csv(Path(__file__).parent / "results" / "kpk_depth.csv", index=False)
    print(table[table.depth.isin([0, 21, 40])].to_string(index=False))
