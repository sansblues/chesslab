"""Read data/cheating/player_games.csv and positions.csv; write the tables in results/."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from chesslab import DATA

RESULTS = Path(__file__).parent / "results"
BANDS = range(1400, 2800, 200)
Z_FPR = stats.norm.isf(1e-4)  # false-positive rate 1 in 10,000
Z_POWER = stats.norm.isf(0.1)  # power 90%


def baseline(classical):
    """Mistakes per game of honest players, by 200-point rating band."""
    rows = [{"band": band, "player_games": len(sub), "mistakes": sub.mistakes.mean()}
            for band in BANDS for sub in [classical[classical.elo // 200 * 200 == band]]]
    return pd.DataFrame(rows)


def spread(classical):
    """Between-player SD of rating-adjusted mistakes per game, by the method of moments, over players
    with at least 6 games; 95% CI from 300 bootstrap samples of players."""
    classical = classical.dropna(subset=["player"])
    elo, opponent = classical.elo / 1000, classical.opponent_elo / 1000
    x = np.c_[np.ones(len(elo)), elo, elo**2, opponent - elo, classical.moves / 40]
    y = classical.mistakes.to_numpy(float)
    residual = y - x @ np.linalg.lstsq(x, y, rcond=None)[0]
    players = pd.Series(residual).groupby(classical.player.to_numpy(), sort=False).agg(["mean", "var", "size"])
    players = players[players["size"] >= 6]
    means, variances, sizes = (players[c].to_numpy() for c in ("mean", "var", "size"))

    def between_variance(i):
        return means[i].var(ddof=1) - variances[i].mean() * (1 / sizes[i]).mean()

    rng = np.random.default_rng(0)
    boot = [between_variance(rng.choice(len(means), len(means))) for _ in range(300)]
    between = np.sqrt(between_variance(slice(None)))
    low, high = np.sqrt(np.maximum(np.percentile(boot, [2.5, 97.5]), 0))
    return pd.DataFrame([{"players": len(means), "games_per_player": sizes.mean(),
                          "within_sd": np.sqrt(variances.mean()), "between_sd": between, "between_sd_low": low,
                          "between_sd_high": high, "detection_floor": Z_FPR * between}])


def games_needed(delta, honest_sd, cheater_sd, between_sd):
    """Fewest games for a test of a player's mean against the honest mean of his rating to reach
    the false-positive rate and the power; inf if no number of games does."""
    n = np.arange(1, 1_000_001)
    threshold = Z_FPR * np.sqrt(honest_sd**2 / n + between_sd**2)
    found = delta - threshold >= Z_POWER * np.sqrt(cheater_sd**2 / n + between_sd**2)
    return n[found.argmax()] if found.any() else np.inf


def engine_every_move(classical, between_sd):
    """Model A: the cheater sees the engine on every move and overrides his k worst moves of each game.
    His mistakes per game fall from m to max(m - k, 0)."""
    rows = []
    for band in BANDS:
        honest = classical[classical.elo // 200 * 200 == band].mistakes
        for k in (1, 2, 3):
            cheater = (honest - k).clip(lower=0)
            delta = honest.mean() - cheater.mean()
            sds = honest.std(ddof=0), cheater.std(ddof=0)
            rows.append({"band": band, "k": k, "mistakes_removed": delta,
                         "games_without_spread": games_needed(delta, *sds, 0),
                         "games_with_spread": games_needed(delta, *sds, between_sd)})
    return pd.DataFrame(rows)


def engine_at_critical_moments(positions):
    """Model B: the cheater asks the engine at k random critical moments of a game (best move in a
    live position, 10-90 win%, at least 10 win% better than the second best). The statistic is the
    number of critical moments missed per game; without the between-player spread."""
    critical = positions.best.between(10, 90) & (positions.best - positions.second >= 10)
    per_game = (positions.assign(critical=critical, missed=critical & ~positions.found)
                .groupby([positions.game, positions.ply % 2])
                .agg(elo=("elo", "first"), moments=("critical", "sum"), missed=("missed", "sum")))
    rows = []
    for band in BANDS:
        sub = per_game[per_game.elo // 200 * 200 == band]
        for k in (1, 2, 3):
            # a random k of the moments: each missed one is fixed with chance min(k, moments) / moments
            fixed = (sub.missed * np.minimum(k, sub.moments) / sub.moments.clip(lower=1)).mean()
            effect = fixed / sub.missed.std(ddof=0)
            rows.append({"band": band, "k": k, "player_games": len(sub), "critical_per_game": sub.moments.mean(),
                         "found": 1 - sub.missed.sum() / sub.moments.sum(), "misses_fixed": fixed,
                         "games": np.ceil(((Z_FPR + Z_POWER) / effect) ** 2)})
    return pd.DataFrame(rows)


def cherry_picking(classical, window=5, players=1000):
    """An honest player's best run of `window` games (lowest mean loss per move) among all his games,
    tested as if it had been chosen in advance. Per-game values drawn from 2000-2399 classical games."""
    x = classical[classical.elo.between(2000, 2399)].eval("loss / moves.clip(lower=1)").to_numpy()
    rng = np.random.default_rng(0)
    null = np.sort(rng.choice(x, (4_000_000, window)).mean(1))
    rows = []
    for games in (10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000):
        sums = np.cumsum(rng.choice(x, (players, games)), axis=1)
        best = np.min(sums[:, window - 1:] - np.c_[np.zeros(players), sums[:, :-window]], axis=1) / window
        p = (np.searchsorted(null, best) + 1) / (len(null) + 1)
        rows.append({"games": games, "players": players, "flagged": np.mean(p < 1e-4), "median_p": np.median(p)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    games = pd.read_csv(DATA / "cheating" / "player_games.csv", dtype={"player": str})
    classical = games[games.speed == "classical"]
    RESULTS.mkdir(exist_ok=True)
    between = spread(classical)
    tables = {"honest_mistakes": baseline(classical), "spread": between,
                  "model_a": engine_every_move(classical, between.between_sd[0]),
                  "model_b": engine_at_critical_moments(pd.read_csv(DATA / "cheating" / "positions.csv")),
                  "cherry_picking": cherry_picking(classical)}
    for name, table in tables.items():
        table.to_csv(RESULTS / f"{name}.csv", index=False, float_format="%.6g")
        print(name, table.to_string(index=False), sep="\n", end="\n\n")
