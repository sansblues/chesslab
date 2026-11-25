"""Rook and two pawns against rook (KRPPvKR): textbook claims over every position, and the pawn
pairs of real games. Reads the tablebase (576 pawn placements, 10.6 G positions, one at a time)
and the Lichess and over-the-board samples; keeps per-file counts in data/endgames/. Writes
results/krppkr_pairs.csv     White's wins per pair of pawn files: quiet positions and real games
results/krppkr_claims.csv    the claims, by side to move
results/krppkr_fh_ranks.csv  f- and h-pawn on the 6th rank or beyond, Black king in front, by rank"""
from multiprocessing import Pool
from pathlib import Path

import chess
import numpy as np
import pandas as pd

from chesslab import DATA, samples, tablebase

import endgame
from endgame import distance, file, rank

HERE = Path(__file__).parent
CACHE = DATA / "endgames"
COUNTS = ["positions", "white_wins"]


def in_front(p):
    """The black king stands ahead of both pawns, on their files or next to them."""
    files = [file(s) for s in p.pawns]
    return (p.quiet & (rank(p.black_king) > max(rank(s) for s in p.pawns))
            & (file(p.black_king) >= min(files) - 1) & (file(p.black_king) <= max(files) + 1))


def blockades(p):
    """The black king stands ahead of a pawn, on its file or next to it."""
    return p.quiet & np.logical_or.reduce(
        [(abs(file(p.black_king) - file(s)) <= 1) & (rank(p.black_king) > rank(s)) for s in p.pawns])


def doubled_cut_off(short):
    """Doubled c- to f-pawns with the white king next to one; the rook on the next file cuts off
    the black king, which stands two files away, ahead of the pawns, on the short or long side."""
    def region(p):
        f = file(p.pawns[0])
        if f != file(p.pawns[1]) or not 3 <= f <= 6:
            return False
        step = (-1 if f <= 4 else 1) * (1 if short else -1)
        return (p.quiet & (file(p.white_rook) == f + step) & (file(p.black_king) == f + 2 * step)
                & (rank(p.black_king) > rank(p.pawns[1]))
                & (np.minimum(*(distance(p.white_king, s) for s in p.pawns)) <= 1))
    return region


REGIONS = {"legal": lambda p: p.legal, "quiet": lambda p: p.quiet, "king in front": in_front,
           "king blockades": blockades, "short side": doubled_cut_off(True), "long side": doubled_cut_off(False)}


def pair(files):
    """Two pawn files as a name, the same for a pair and its mirror image: f+h is a+c."""
    files = min(sorted(files), sorted(9 - f for f in files))
    return "+".join("abcdefgh"[f - 1] for f in files)


def tally(part):
    """White's wins in each region of one slice, by side to move."""
    rows, wins = [], part.white_wins
    for name, region in REGIONS.items():
        selected = endgame.mask(region, part)
        for turn in range(2) if selected is not None else ():
            here = selected[turn]
            rows.append({"pawn_1": part.pawns[0], "pawn_2": part.pawns[1], "weight": part.weight, "region": name,
                         "white_to_move": turn == 0, "positions": np.count_nonzero(here),
                         "white_wins": np.count_nonzero(here & wins[turn])})
    return rows


def tablebase_counts():
    folder = CACHE / "krppkr"
    folder.mkdir(parents=True, exist_ok=True)
    for part in endgame.slices("KRPPvKR"):
        path = folder / f"{part.pawns[0]}_{part.pawns[1]}.csv"
        if not path.exists():
            pd.DataFrame(tally(part)).to_csv(path.with_suffix(".part"), index=False)
            path.with_suffix(".part").rename(path)
    counts = pd.concat(pd.read_csv(p) for p in sorted(folder.glob("*.csv")))
    counts[COUNTS] = counts[COUNTS].mul(counts.weight, axis=0)
    files = [file(counts.pawn_1), file(counts.pawn_2)]
    counts["pair"] = [pair(f) for f in zip(*files)]
    counts["apart"] = abs(files[0] - files[1])
    counts["rank_1"], counts["rank_2"] = rank(counts.pawn_1), rank(counts.pawn_2)
    counts["side_to_move"] = np.where(counts.white_to_move, "White", "Black")
    return counts


def entry(game):
    """The first tablebase position of a game, if it is rook and two pawns against rook: the
    pawn pair, and whether the side with the pawns wins with best play."""
    pieces = 32 - np.cumsum(["x" in san for san in game.sans])
    if pieces[-1] > 6:
        return None
    board, value = chess.Board(), None
    try:
        for ply, san in enumerate(game.sans):
            board.push_san(san)
            if pieces[ply] <= 6 and (value := tablebase.wdl(board)) is not None:
                break
    except ValueError:  # an illegal move in the record
        return None
    symbols = "".join(sorted(piece.symbol() for piece in board.piece_map().values()))
    if value is None or symbols not in ("KPPRkr", "KRkppr"):
        return None
    pawns = board.pieces(chess.PAWN, symbols == "KPPRkr")
    return pair([file(s) for s in pawns]), value == (1 if board.turn == (symbols == "KPPRkr") else -1)


def game_entries(task):
    source, path = task
    out = CACHE / "games" / f"{source}_{path.name.split('.')[0]}.csv"
    if not out.exists():
        games = samples.lichess(path) if source == "lichess" else samples.otb_file(path)
        rows = [(game.key, *found) for game in games if (found := entry(game))]
        pd.DataFrame(rows, columns=["key", "pair", "white_wins"]).to_csv(out.with_suffix(".part"), index=False)
        out.with_suffix(".part").rename(out)
    return pd.read_csv(out).assign(source=source)


def game_counts():
    """White's (the pawns') wins in real games, by pawn pair. An over-the-board game relayed
    several times counts once."""
    (CACHE / "games").mkdir(parents=True, exist_ok=True)
    tasks = [("lichess", p) for p in samples.lichess_files()] + [("otb", p) for p in samples.broadcast_files()]
    with Pool(12) as pool:
        found = pd.concat(pool.imap(game_entries, tasks, chunksize=1))
    found = pd.concat([found[found.source == "lichess"], found[found.source == "otb"].drop_duplicates("key")])
    return found.groupby("pair").white_wins.agg(games="size", game_wins="sum")


def main():
    counts = tablebase_counts()
    quiet = counts[counts.region == "quiet"]
    pairs = pd.concat([quiet[quiet.white_to_move == turn].groupby("pair")[COUNTS].sum()
                       .add_suffix(suffix) for turn, suffix in ((True, "_white_to_move"), (False, "_black_to_move"))]
                      + [game_counts()], axis=1)
    pairs.round().astype(int).to_csv(HERE / "results" / "krppkr_pairs.csv")

    lowest = np.minimum(counts.rank_1, counts.rank_2)
    claims = {
        "all positions": counts.region == "legal",
        "two rook pawns (a+h)": (counts.pair == "a+h") & (counts.region == "quiet"),
        "two rook pawns, Black king blockading a pawn": (counts.pair == "a+h") & (counts.region == "king blockades"),
        "doubled pawns, Black king cut off on the short side": counts.region == "short side",
        "doubled pawns, Black king cut off on the long side": counts.region == "long side",
        "doubled pawns, Black king in front": (counts.apart == 0) & (counts.region == "king in front"),
        "connected pawns": (counts.apart == 1) & (counts.region == "quiet"),
        "f+h pawns on the 6th rank or beyond": (counts.pair == "a+c") & (lowest >= 6) & (counts.region == "quiet"),
        "f+h pawns on the 6th rank or beyond, Black king in front":
            (counts.pair == "a+c") & (lowest >= 6) & (counts.region == "king in front"),
    }
    table = pd.concat(counts[m].groupby("side_to_move", sort=False)[COUNTS].sum().round().astype(int).assign(claim=name)
                      for name, m in claims.items()).reset_index()[["claim", "side_to_move", *COUNTS]]
    table.to_csv(HERE / "results" / "krppkr_claims.csv", index=False)

    fh = counts[(counts.pair == "a+c") & (lowest >= 6) & (counts.region == "king in front")].copy()
    rook_pawn = file(fh.pawn_1).isin([1, 8])
    fh["rook_pawn_rank"] = np.where(rook_pawn, fh.rank_1, fh.rank_2)
    fh["bishop_pawn_rank"] = np.where(rook_pawn, fh.rank_2, fh.rank_1)
    fh = fh.groupby(["rook_pawn_rank", "bishop_pawn_rank", "side_to_move"], sort=False)[COUNTS].sum()
    fh.round().astype(int).reset_index().to_csv(HERE / "results" / "krppkr_fh_ranks.csv", index=False)
    print(table.assign(win_rate=table.white_wins / table.positions).to_string(index=False))


if __name__ == "__main__":
    main()
