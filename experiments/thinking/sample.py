"""Choose the players, games and positions of the test, as planned (PLAN.md).
Reads the broadcast games of the baseline year (Jul 2024 - Jun 2025) and the FIDE lists jul25, jul26.
Writes data/thinking/game_sides.parquet (every baseline game-side of the eligible players: time and
error) and data/thinking/positions.parquet (4,000 players x 6 games: the positions to analyse)."""
from multiprocessing import Pool

import chess
import numpy as np
import pandas as pd

from chesslab import DATA, games, samples
from chesslab.games import win_chance

OUT = DATA / "thinking"
BASELINE = samples.broadcast_files()[:12]  # 2024-07 ... 2025-06


def online(game):
    """The planned online filter: the core's pattern on BroadcastName, Event and Site together."""
    h = game.headers
    text = (h.get("BroadcastName") or "")[:100] + " " + h.get("Event", "")[:100] + " @" + h.get("Site", "")[:60]
    return bool(samples.ONLINE.search(text)) or max(game.white_elo or 0, game.black_elo or 0) > 2900


def floats(values):
    return np.array([np.nan if v is None else v for v in values], np.float32)


def qualifies(game, clocks, evals):
    """Classical, with a result, >= 90% of plies with a clock and an eval, clocks to the second."""
    known = clocks[~np.isnan(clocks)]
    return (game.result is not None and not online(game) and games.otb_speed(game.clocks) == "classical"
            and np.mean(~np.isnan(clocks)) >= 0.9 and len(known) > 0 and np.mean(known % 60 != 0) > 0.2
            and np.mean(~np.isnan(evals)) >= 0.9)


def read_month(path):
    """(key, game or None) for every standard game of >= 20 plies, in file order; None if it does not
    qualify. These are the planned rules, not samples.otb(): duplicates are removed before filtering, and
    a non-start FEN is allowed. samples.otb() would change 9 of 146,773 games, and so the random draws."""
    rows = []
    for game in games.read(path):
        if game.headers.get("Variant", "Standard") not in ("Standard", "") or len(game.sans) < 20:
            continue
        clocks, evals = floats(game.clocks), floats(game.evals)
        rows.append((game.key, {
            "white_fide": game.white_fide, "black_fide": game.black_fide, "white_elo": game.white_elo,
            "black_elo": game.black_elo, "result": game.result, "sans": " ".join(game.sans[:80]),
            "clocks": clocks[:80], "evals": evals[:80]} if qualifies(game, clocks, evals) else None))
    return rows


def increment(clocks):
    """95th percentile of the clock gain over one move before move 39, rounded to 5 s, 0 to 60 s."""
    gains = clocks[2:78] - clocks[:len(clocks[2:78])]
    gains = gains[~np.isnan(gains)]
    return float(min(max(0, 5 * round(np.percentile(gains, 95) / 5)), 60)) if len(gains) else 0.0


def own_moves(clocks, evals, color, inc):
    """The player's moves 9 to 40: (ply, think time, clock before, eval before, eval after), evals
    for the mover. A move is dropped without both clocks, after a time addition, or with an
    impossible time."""
    sign = 1 if color == 0 else -1
    moves = []
    for ply in range(16 + color, min(len(clocks), 80), 2):
        before, after = clocks[ply - 2], clocks[ply]
        if np.isnan(before) or np.isnan(after) or after - before > inc + 120:
            continue
        t = before - after + inc
        if -2 <= t <= 3600:
            moves.append((ply, max(t, 0.0), float(before), evals[ply - 1] * sign, evals[ply] * sign))
    return moves


def side_features(game, color):
    """Mean log think time, error (mean win-probability loss, stored evals) and time trouble
    (< 5 min before move 40) of one game-side; None under 5 moves."""
    moves = own_moves(game.clocks, game.evals, color, game.increment)
    if len(moves) < 5:
        return None
    t, before, after = (np.array([m[i] for m in moves]) for i in (1, 3, 4))
    ok = ~np.isnan(before) & ~np.isnan(after) & (np.abs(before) < 9000)
    loss = np.maximum(0, win_chance(before[ok]) - win_chance(after[ok])) if ok.any() else np.array([np.nan])
    own = game.clocks[color:80:2]
    own = own[~np.isnan(own)]
    return {"mean_log_time": float(np.mean(np.log1p(t))), "error": float(np.mean(loss)),
                "time_trouble": bool(len(own) and own.min() < 300)}


def positions(game, color):
    """The positions of the player's moves 9 to 40 with more than one legal move."""
    moves = {m[0]: m for m in own_moves(game.clocks, game.evals, color, game.increment)}
    board, rows = chess.Board(), []
    for ply, san in enumerate(game.sans.split()):
        try:
            move = board.parse_san(san)
        except ValueError:
            break
        if ply in moves and board.legal_moves.count() > 1:
            _, t, clock, before, after = moves[ply]
            rows.append((ply, t, clock, before, after, board.fen(), move.uci()))
        board.push(move)
    return rows


def main():
    with Pool(12) as pool:
        months = pool.map(read_month, BASELINE)
    seen, kept = set(), []
    for key, game in (row for month in months for row in month):  # a game counts once: its first relay
        if key not in seen:
            seen.add(key)
            if game:
                kept.append(game)
    del months
    G = pd.DataFrame(kept).rename_axis("game").reset_index()
    print("qualifying baseline games", len(G))

    # eligible: >= 10 qualifying baseline games, rated in the jul25 and jul26 lists
    rated = set(samples.fide("jul25").id) & set(samples.fide("jul26").id)
    sides = pd.concat([G[["game", "white_fide"]].set_axis(["game", "fide_id"], axis=1).assign(color=0),
                       G[["game", "black_fide"]].set_axis(["game", "fide_id"], axis=1).assign(color=1)]).dropna()
    sides["fide_id"] = sides.fide_id.astype("int64")
    counts = sides.fide_id.value_counts()
    sides = sides[sides.fide_id.isin([f for f in counts[counts >= 10].index if f in rated])]
    print("eligible players", sides.fide_id.nunique(), "game-sides", len(sides))

    G = G.set_index("game")
    G["increment"] = G.clocks.map(increment)
    features = []
    for s in sides.itertuples():
        game = G.loc[s.game]
        if f := side_features(game, s.color):
            white = s.color == 0
            features.append(dict(fide_id=s.fide_id, game=s.game, color=s.color,
                                 elo=game.white_elo if white else game.black_elo,
                                 opponent_elo=game.black_elo if white else game.white_elo,
                                 score=game.result if white else 1 - game.result, **f))
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(features).to_parquet(OUT / "game_sides.parquet", index=False)

    # up to 10 random game-sides per player (seed 7), then 4,000 random players (seed 11) x 6 game-sides
    chosen = sides.sample(frac=1, random_state=7).groupby("fide_id").head(10)
    rows = []
    for s in chosen.itertuples():
        game = G.loc[s.game]
        elo = game.white_elo if s.color == 0 else game.black_elo
        rows += [(s.fide_id, s.game, s.color, elo, *p) for p in positions(game, s.color)]
    P = pd.DataFrame(rows, columns=["fide_id", "game", "color", "elo", "ply", "think_time", "clock_before",
                                    "eval_before", "eval_after", "fen", "move"])
    players = P.fide_id.unique()
    np.random.default_rng(11).shuffle(players)
    P = P[P.fide_id.isin(players[:4000])]
    six = P[["fide_id", "game"]].drop_duplicates().sample(frac=1, random_state=11).groupby("fide_id").head(6)
    P = P.merge(six, on=["fide_id", "game"])
    P = P.sort_values(["fide_id", "game", "ply"])
    P.to_parquet(OUT / "positions.parquet", index=False)
    print("positions", len(P), "unique", P.fen.nunique())


if __name__ == "__main__":
    main()
