"""Philidor defence, followed literally (the textbook recipe, as on Wikipedia), for Black against
rook and pawn:
- keep the king on the pawn's queening square or next to it; when checked, step to another one;
- while the pawn is below the 6th rank, keep the rook on the 6th rank;
- once the pawn reaches the 6th rank, check the king from behind, or take the rook to the 1st rank.
Ties go to the square farthest from the white king. START is the textbook position."""
import chess

from endgame import distance, file, rank

MATERIAL = "KRPvKR"
START = "3k4/7R/r7/3PK3/8/8/8/8 b - - 0 1"


def policy(board: chess.Board) -> chess.Move | None:
    king, rook = board.king(chess.BLACK), next(iter(board.pieces(chess.ROOK, chess.BLACK)))
    white_king, pawn = board.king(chess.WHITE), next(iter(board.pieces(chess.PAWN, chess.WHITE)))
    queening = pawn % 8 + 56
    king_moves = [m for m in board.legal_moves if m.from_square == king]
    rook_moves = [m for m in board.legal_moves if m.from_square == rook]
    home = [m for m in king_moves if rank(m.to_square) >= 7 and abs(file(m.to_square) - file(pawn)) <= 1]

    def safe(move):
        """The rook's new square is not attacked, or the king defends it."""
        board.push(move)
        attacked = board.is_attacked_by(chess.WHITE, move.to_square)
        board.pop()
        return not attacked or distance(move.to_square, king) <= 1

    def best(moves, *keys):
        return min(moves, key=lambda m: (*(k(m.to_square) for k in keys), -distance(m.to_square, white_king),
                                         m.uci()), default=None)

    def go_home():
        return best(home, lambda s: distance(s, queening))

    if board.is_check():
        return go_home()
    if rank(pawn) <= 5:
        return best([m for m in rook_moves if rank(m.to_square) == 6 and safe(m)]) or go_home()
    checks = [m for m in rook_moves if rank(m.to_square) < rank(white_king) and board.gives_check(m) and safe(m)]
    if checks:
        return best(checks)
    if rank(rook) > 1:
        return best([m for m in rook_moves if rank(m.to_square) == 1 and safe(m)],
                    lambda s: file(s) != file(rook)) or go_home()
    return go_home()
