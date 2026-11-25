"""Rule of five (Soltis 2003, Mednis 1998, quoted via Wikipedia). The pawn is protected and the
defending king is cut off along a file: add the pawn's rank and the number of files the king is
cut off. More than five usually wins; otherwise it is normally a draw.

Region R5, the most charitable reading (ours): a c- to f-pawn on ranks 2-6, protected by its king,
which is not ahead of it; the white rook cuts the black king off on the long side, alone on its
file and safe from the king; the black king is level with the pawn or ahead of it; the black rook
stands in front of the pawn on the back rank; quiet; White to move."""
from endgame import distance, file, rank

MATERIAL = "KRPvKR"


def files_cut_off(p):
    return abs(file(p.black_king) - file(p.pawn)) - 1


def total(p):
    return rank(p.pawn) + files_cut_off(p)


def cut_off(p):
    """R5 without its last three conditions: any b- to g-pawn, either side, either side to move."""
    pawn, rook = p.pawn, p.white_rook
    if not (2 <= file(pawn) <= 7 and rank(pawn) <= 6):
        return False
    return (p.quiet & (distance(p.white_king, pawn) == 1) & (rank(p.white_king) <= rank(pawn))
            & ((file(rook) - file(pawn)) * (file(rook) - file(p.black_king)) < 0)
            & (file(p.white_king) != file(rook)) & (distance(p.black_king, rook) >= 2)
            & (rank(p.black_king) >= rank(pawn)) & (p.black_rook == pawn % 8 + 56))


def long_side(p):
    """The black king is on the side of the pawn with more files."""
    return (file(p.black_king) > file(p.pawn)) == (file(p.pawn) <= 4)


def region(p):
    return 3 <= file(p.pawn) <= 6 and cut_off(p) & long_side(p) & p.white_to_move


def rule_of_five(p):
    return total(p) > 5


def sharpened(p):
    """Ours: sum 6 or more and the cutting rook below the pawn's rank."""
    return (total(p) >= 6) & (rank(p.white_rook) < rank(p.pawn))


RULES = (rule_of_five,)
WIN_CLAIMS = (sharpened,)
