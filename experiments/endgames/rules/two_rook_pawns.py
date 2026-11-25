"""Two rook pawns: rook and a- and h-pawns against rook "are often a draw" (Wikipedia, citing Emms,
Nunn, Müller and Lamprecht).

Region (ours): an a-pawn and an h-pawn, quiet positions, either side to move."""
from endgame import file

MATERIAL = "KRPPvKR"


def region(p):
    return sorted(file(s) for s in p.pawns) == [1, 8] and p.quiet


def often_a_draw(p):
    return False


RULES = (often_a_draw,)
