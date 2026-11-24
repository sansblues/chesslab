"""Syzygy tablebases: python-chess for single probes, Fathom (C) to enumerate whole tables."""
import ctypes
from functools import cache

import chess
import chess.syzygy
import numpy as np

from chesslab import DATA, ROOT

SYZYGY = DATA / "syzygy"
PIECE_CODES = {"P": 1, "N": 2, "B": 3, "R": 4, "Q": 5, "K": 6}


@cache
def syzygy() -> chess.syzygy.Tablebase:
    return chess.syzygy.open_tablebase(str(SYZYGY))


def wdl(board: chess.Board) -> int | None:
    """Value for the side to move: 1 win, 0 draw, -1 loss, with best play and the half-move clock
    at 0. A cursed win or a blessed loss (decided only past the 50-move rule) counts as a draw.
    None if unknown: castling rights, too many pieces or a table not in data/syzygy."""
    if board.is_checkmate():
        return -1
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    if board.castling_rights:
        return None
    try:
        value = syzygy().probe_wdl(board)
    except (KeyError, IndexError, ValueError, chess.syzygy.MissingTableError):
        return None
    return 1 if value == 2 else -1 if value == -2 else 0


@cache
def _fathom():
    lib = ctypes.CDLL(str(ROOT / "build" / "fathom.so"))
    lib.fathom_init.argtypes = [ctypes.c_char_p]
    lib.fathom_wdl.argtypes = lib.fathom_dtz.argtypes = [ctypes.c_uint64] * 8 + [ctypes.c_int]
    lib.fathom_dump.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_void_p]
    lib.fathom_dump.restype = ctypes.c_long
    if lib.fathom_init(str(SYZYGY).encode()) < 3:
        raise RuntimeError(f"Fathom found no tables in {SYZYGY}")
    return lib


def _bitboards(board):
    return (board.occupied_co[chess.WHITE], board.occupied_co[chess.BLACK], board.kings, board.queens,
            board.rooks, board.bishops, board.knights, board.pawns, board.turn == chess.WHITE)


def fathom_wdl(board: chess.Board) -> int | None:
    """Syzygy WDL from the side to move, -2..2 (±1: cursed win, blessed loss), via Fathom.
    The half-move clock, castling rights and en passant are taken as none. None if it fails."""
    value = _fathom().fathom_wdl(*_bitboards(board))
    return None if value in (98, 99) else value


def fathom_dtz(board: chess.Board) -> int | None:
    """Syzygy DTZ from the side to move, via Fathom. None if it fails."""
    value = _fathom().fathom_dtz(*_bitboards(board))
    return None if value in (9998, 9999) else value


def enumerate_wdl(signature: str) -> np.ndarray:
    """Code of every placement of the pieces of a signature such as "KRPvKR", both sides to move:
    0..4 = WDL + 2 from the side to move, 5 = two pieces on one square, 6 = illegal, 7 = failed.
    Axes: side to move (0 White), then the square of each piece in signature order. A pawn's
    axis has 48 squares (a2..h7); the first pawn's has 24 (a2..d7 by rank, then file: the other
    half is the mirror image)."""
    white, black = signature.split("v")
    codes = [PIECE_CODES[p] for p in white] + [8 + PIECE_CODES[p] for p in black]
    shape, pawns = [2], 0
    for code in codes:
        shape.append(64 if code & 7 != 1 else 48 if pawns else 24)
        pawns += code & 7 == 1
    out = np.empty(shape, dtype=np.int8)
    failures = _fathom().fathom_dump(len(codes), (ctypes.c_int * len(codes))(*codes), out.ctypes.data)
    if failures:
        raise RuntimeError(f"{failures} failed probes in {signature}")
    return out
