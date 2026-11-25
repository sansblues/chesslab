"""Tablebase slices as numpy arrays, for the rule checker and the analyses. A slice holds every
position of a material with White's pawns on fixed squares: both sides to move, every placement of
the other pieces, with its Syzygy value and a quiet flag (slices.c, via Fathom). Positions count
up to the a-h mirror, as on syzygy-tables.info: a pawn placement and its mirror image make one slice."""
import ctypes
import importlib.util
import itertools
import os
from functools import cache, cached_property

import chess
import numpy as np
import pandas as pd

from chesslab import DATA
from chesslab.tablebase import PIECE_CODES, SYZYGY

os.environ.setdefault("OMP_NUM_THREADS", "12")
LIBRARY = DATA / "endgames" / "slices.so"
NAMES = {"K": "king", "Q": "queen", "R": "rook", "B": "bishop", "N": "knight"}


def file(square):
    return square % 8 + 1  # a = 1


def rank(square):
    return square // 8 + 1


def distance(a, b):
    """King moves from square a to square b."""
    return np.maximum(abs(file(a) - file(b)), abs(rank(a) - rank(b)))


@cache
def _library():
    if not LIBRARY.exists():
        raise FileNotFoundError(f"{LIBRARY} is missing: run make -C experiments/endgames slices")
    lib = ctypes.CDLL(str(LIBRARY))
    lib.slices_probe.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_uint64,
                                 ctypes.c_void_p, ctypes.c_void_p]
    lib.slices_probe.restype = ctypes.c_long
    if lib.slices_init(str(SYZYGY).encode()) < 3:
        raise RuntimeError(f"Fathom found no tables in {SYZYGY}")
    return lib


class Slice:
    """The positions of a material with White's pawns on given squares.

    pawns: the pawn squares (ints, a1 = 0), and pawn if there is one. The other pieces are numpy
    arrays of squares named like white_king or black_rook; with white_to_move they broadcast over
    the slice, axes (side to move, then each piece). legal, quiet and white_wins are boolean arrays
    of the slice's shape. A cursed win (won only past the 50-move rule) counts as a draw."""

    def __init__(self, material, pawns, weight):
        white, black = material.split("v")
        pieces = [(colour, piece) for colour, side in enumerate((white, black)) for piece in side if piece != "P"]
        assert "P" not in black and len(set(pieces)) == len(pieces), "unsupported material"
        self.material, self.pawns, self.weight = material, pawns, weight
        if len(pawns) == 1:
            self.pawn = pawns[0]
        self.shape = (2,) + (64,) * len(pieces)
        self.white_to_move = np.array([True, False]).reshape((2,) + (1,) * len(pieces))
        self.names = [("white_", "black_")[colour] + NAMES[piece] for colour, piece in pieces]
        self._codes = [colour * 8 + PIECE_CODES[piece] for colour, piece in pieces]
        for axis, name in enumerate(self.names, 1):
            setattr(self, name, np.arange(64).reshape([64 if i == axis else 1 for i in range(len(self.shape))]))

    @cached_property
    def _probe(self):
        wdl, quiet = np.empty(self.shape, np.int8), np.empty(self.shape, np.bool_)
        failures = _library().slices_probe(len(self._codes), (ctypes.c_int * len(self._codes))(*self._codes),
                                           sum(1 << s for s in self.pawns), wdl.ctypes.data, quiet.ctypes.data)
        if failures:
            raise RuntimeError(f"{failures} failed probes in {self.material} with pawns {self.pawns}")
        return wdl, quiet

    @property
    def legal(self):
        return self._probe[0] <= 4

    @property
    def quiet(self):
        """Legal, the side to move is not in check and has no capture that leaves the capturing
        piece safe, and no piece other than a king or pawn is attacked and undefended."""
        return self._probe[1]

    @property
    def white_wins(self):
        wdl = self._probe[0]
        return np.where(self.white_to_move, wdl == 4, wdl == 0)

    def board(self, index) -> chess.Board:
        """The position at a flat index of the slice."""
        turn, *squares = np.unravel_index(index, self.shape)
        board = chess.Board(None)
        for square in self.pawns:
            board.set_piece_at(square, chess.Piece(chess.PAWN, chess.WHITE))
        for square, code in zip(squares, self._codes):
            board.set_piece_at(int(square), chess.Piece(code & 7, code < 8))
        board.turn = bool(turn == 0)
        return board


def slices(material):
    """Every slice of a material with White pawns, one per pawn placement up to the mirror."""
    for pawns in itertools.combinations(range(8, 56), material.split("v")[0].count("P")):
        mirror = tuple(sorted(s ^ 7 for s in pawns))
        if pawns <= mirror:
            yield Slice(material, pawns, 0.5 if pawns == mirror else 1.0)


def mask(region, part: Slice):
    """The region's positions in a slice (boolean array), or None if it has none. A region may
    return a plain False for a whole slice, e.g. for the wrong pawn squares."""
    selected = region(part)
    if not np.any(selected):
        return None
    return np.broadcast_to(selected, part.shape) & part.legal


def table(material, region, **features) -> pd.DataFrame:
    """The positions of a region, one row each: pawn and piece squares, white_to_move, white_wins,
    weight, and one column per feature (a function of a slice, like a region)."""
    frames = []
    for part in slices(material):
        selected = mask(region, part)
        if selected is None:
            continue
        index = np.flatnonzero(selected)
        turn, *squares = np.unravel_index(index, part.shape)
        columns = {"pawn" if len(part.pawns) == 1 else f"pawn_{i}": s for i, s in enumerate(part.pawns)}
        columns |= dict(zip(part.names, squares))
        columns |= {"white_to_move": turn == 0, "white_wins": part.white_wins.ravel()[index], "weight": part.weight}
        columns |= {name: np.broadcast_to(f(part), part.shape).ravel()[index] for name, f in features.items()}
        frames.append(pd.DataFrame(columns))
    return pd.concat(frames, ignore_index=True)


def load(path):
    """A rule file as a module."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
