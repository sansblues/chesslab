"""How clock time at move 20 goes with the result: within-player models on the game-sides of extract.py.

Reads data/clock/. Writes results/value_curve.csv, results/value.csv and results/effects.csv.
Values are in expected score per game: 0.01 is 1 point per 100 games."""
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from chesslab import DATA
from chesslab.games import expected_score, win_chance

IN = DATA / "clock"
RESULTS = Path(__file__).parent / "results"
C = 20  # the checkpoint: the side's 20th move
DELTA = 0.10  # the extra clock: 10% of the budget
CLOCK_KNOTS = (0.10, 0.25, 0.40, 0.55)
CHANCE_KNOTS = (0.2, 0.4, 0.6, 0.8)
Z = 1.959964  # 95% intervals
ELO = np.log(10) / 1600  # expected score per Elo point between equal players
ONLINE_CONTROLS = {"blitz": ["180+0", "300+0", "180+2", "300+3"], "rapid": ["600+0", "900+0", "600+5", "900+10"]}


class Within:
    """Least squares within players (player fixed effects), standard errors clustered by player (CR1)."""

    def __init__(self, X, players):
        self.group, self.players = pd.factorize(players)
        self.size = np.bincount(self.group)
        names, X = X.columns, self.demean(X.to_numpy(float, copy=True))
        gram = X.T @ X
        keep = []  # drop columns constant within players or linear in earlier columns
        for j in range(X.shape[1]):
            rest = gram[j, j] - gram[j, keep] @ np.linalg.solve(gram[np.ix_(keep, keep)], gram[keep, j])
            if gram[j, j] > 1e-18 * len(X) and rest > 1e-7 * gram[j, j]:
                keep.append(j)
        self.names = names[keep]
        self.X = X if len(keep) == X.shape[1] else X[:, keep]

    def demean(self, a):
        """Subtract each player's mean, in place."""
        for column in a.reshape(len(a), -1).T:
            column -= (np.bincount(self.group, column) / self.size)[self.group]
        return a

    def fit(self, y):
        """Coefficients and their covariance; self.influence: each player's share of the coefficients' error."""
        y = self.demean(np.array(y, float))
        bread = np.linalg.inv(self.X.T @ self.X)
        b = bread @ (self.X.T @ y)
        e = y - self.X @ b
        self.influence = pd.DataFrame(np.column_stack([np.bincount(self.group, x * e) for x in self.X.T]) @ bread,
                                      self.players, self.names)
        (n, k), groups = self.X.shape, len(self.size)
        V = groups / (groups - 1) * (n - 1) / (n - k) * self.influence.T @ self.influence
        return pd.Series(b, self.names), V


def clustered_se(influence):
    """Standard error from each player's influence on an estimate."""
    groups = len(influence)
    return np.sqrt(groups / (groups - 1) * np.sum(influence ** 2))


def iv(y, x, z, W, players):
    """Just-identified two-stage least squares of y on x with instrument z, within players, controls W;
    the estimate, its standard error clustered by player, and each player's influence on it."""
    m = Within(pd.concat([pd.DataFrame({"y": y, "x": x, "z": z}), W], axis=1), players)
    data, W = m.X[:, :3], m.X[:, 3:]
    y, x, z = (data - W @ np.linalg.lstsq(W, data, rcond=None)[0]).T
    b = z @ y / (z @ x)
    influence = pd.Series(np.bincount(m.group, z * (y - b * x)) / (z @ x), m.players)
    return b, clustered_se(influence), influence


def linear(fit, weights):
    """Estimate and standard error of a weighted sum of coefficients."""
    b, V = fit
    return weights @ b[weights.index], np.sqrt(weights @ V.loc[weights.index, weights.index] @ weights)


def spline(x, knots, name):
    x = np.asarray(x, float)
    return pd.DataFrame({f"{name}_0": x, **{f"{name}_{j}": np.maximum(0, x - k) for j, k in enumerate(knots, 1)}})


def gain(clock_left):
    """Mean change of the clock spline when DELTA is added to the clock left (at most 1)."""
    return (spline(np.minimum(clock_left + DELTA, 1), CLOCK_KNOTS, "clock")
            - spline(clock_left, CLOCK_KNOTS, "clock")).mean()


def dummies(values, name):
    return pd.get_dummies(values.astype(str), prefix=name, drop_first=True, dtype=float)


def ratings(df):
    return pd.DataFrame({"elo": df.elo / 100, "elo_difference": (df.elo - df.opponent_elo) / 100, "black": df.color})


def design(df):
    """Model G: the clock spline, ratings, the opponent's clock, the position after move 20, the setting."""
    control = df.base.astype(str) + "+" + df.increment.astype(str)
    if "extra_time" in df:
        control += "|" + df.extra_time.astype(str)
    control = control.where(control.map(control.value_counts()) >= 1000, "other")
    parts = [spline(df.clock_left, CLOCK_KNOTS, "clock"), ratings(df),
             spline(df.opponent_clock_left, CLOCK_KNOTS, "opponent_clock"),
             df[["legal_moves", "captures_checks", "material"]], df.volatility.fillna(df.volatility.mean()),
             spline(df.win_chance, CHANCE_KNOTS, "win_chance"), dummies(control, "control")]
    if "month" in df:
        parts += [dummies(df.month, "month"), dummies(pd.cut(df["round"], [-10, 1, 3, 6, 1000]), "round")]
    else:
        parts += [dummies(df.hour, "hour"), df.has_evals.astype(float)]
    return pd.concat([part.astype(np.float32) for part in parts], axis=1)  # float32: memory


def repeated(df):
    """Sides of players with two or more of them: a player with one side carries no within-player information."""
    return df[df.groupby("player").player.transform("size") >= 2].reset_index(drop=True)


def prepare(sides):
    sides = repeated(sides)
    sides["y"] = sides.score - expected_score(sides.elo, sides.opponent_elo)
    sides["clock_left"] = sides.clock_left.clip(upper=1)
    sides["opponent_clock_left"] = sides.opponent_clock_left.clip(upper=1)
    return sides


def habitually_short(df):
    """Players with 10 or more sides whose median clock left is in the lowest fifth of such players."""
    sides = df.groupby("player").size()
    median = df.groupby("player").clock_left.median()[sides >= 10]
    return df.player.isin(median.index[median <= median.quantile(0.2)]).to_numpy()


def effect(population, name, df, estimate, se=np.nan, base_rate=np.nan):
    return {"population": population, "effect": name, "estimate": estimate, "low": estimate - Z * se,
            "high": estimate + Z * se, "base_rate": base_rate, "game_sides": len(df), "players": df.player.nunique()}


def value(population, model, evaluated, controls, outcome):
    """Gross value of DELTA more clock at move 20 (model G), its early cost from the time-control IV, and the net,
    for all players and for the habitually short; the clock curve; the change of one outcome (time trouble or loss
    on time)."""
    m = Within(design(model), model.player)
    fit, influence = m.fit(model.y), m.influence
    curve = []
    for x in np.arange(1, 7) / 10:
        estimate, se = linear(fit, gain(np.array([x])))
        curve.append({"clock_left": x, "gain": estimate, "gain_low": estimate - Z * se, "gain_high": estimate + Z * se})

    errors = Within(pd.concat([evaluated[["error", "opponent_error"]], ratings(evaluated)], axis=1), evaluated.player)
    score_per_error = -errors.fit(evaluated.y)[0]["error"]
    per_minute, per_minute_se, per_minute_influence = iv(controls.early_error / C, controls.minutes_used,
                                                         np.log(controls.budget), ratings(controls), controls.player)
    effects = [effect(population, "score_per_error", evaluated, score_per_error),
               effect(population, "early_error_per_minute", controls, per_minute, per_minute_se),
               effect(population, outcome, model, *linear(m.fit(model[outcome].astype(float)), gain(model.clock_left)),
                      model[outcome].mean())]

    rows = []  # net = gross + per_minute * score_per_error * minutes; its error from all three (delta method)
    for group, mask in (("all", np.ones(len(model), bool)), ("habitually_short", habitually_short(model))):
        weights = gain(model.clock_left[mask])
        gross, gross_se = linear(fit, weights)
        minutes = C * DELTA * model.budget[mask].mean() / 60  # the minutes saved, times the C early moves
        cost = -per_minute * score_per_error * minutes
        net = gross - cost
        net_se = clustered_se((influence[weights.index] @ weights)
                              .add(minutes * score_per_error * per_minute_influence, fill_value=0)
                              .add(-minutes * per_minute * errors.influence["error"], fill_value=0))
        rows.append({"population": population, "group": group, "game_sides": mask.sum(),
                     "players": model.player[mask].nunique(), "median_clock_left": model.clock_left[mask].median(),
                     "time_trouble": model.time_trouble[mask].mean(),
                     "gross": gross, "gross_low": gross - Z * gross_se, "gross_high": gross + Z * gross_se,
                     "early_cost": cost, "net": net, "net_low": net - Z * net_se, "net_high": net + Z * net_se,
                     "net_elo": net / ELO})
    return rows, effects, curve


def book_depth():
    """Per side: own moves (in the first 40 plies) along a line that the player reached with the same colour in an
    earlier game, and the number of earlier games with that colour."""
    openings = pd.concat([pd.read_parquet(f) for f in sorted((IN / "openings").glob("*.parquet"))])
    openings = openings.drop_duplicates("key")
    openings["round_number"] = pd.to_numeric(openings["round"].str.extract(r"(\d+)")[0], errors="coerce").fillna(0)
    tables = []
    for color, player in ((0, "white_fide"), (1, "black_fide")):
        games = openings.dropna(subset=[player]).sort_values([player, "date", "round_number"])
        plies, earlier = np.zeros(len(games), int), np.zeros(len(games), int)
        previous = None
        for i, (fide, moves) in enumerate(zip(games[player], games.moves)):
            if fide != previous:
                previous, seen, count = fide, set(), 0
            lines = list(itertools.accumulate(moves.split(), lambda line, san: line + " " + san))
            plies[i] = next((n for n, line in enumerate(lines) if line not in seen), len(lines))
            earlier[i], count = count, count + 1
            seen.update(lines)
        tables.append(pd.DataFrame({"key": games.key.to_numpy(), "color": color,
                                    "book_moves": (plies + 1 - color) // 2, "earlier_games": earlier}))
    return pd.concat(tables)


def natural_experiments(sides):
    """Book depth as an instrument for the clock, late starts, and 60+30 against 90+30 for the same players."""
    population, effects = "otb_classical", []
    book = repeated(sides.merge(book_depth(), on=["key", "color"]).dropna(subset=["win_chance"]))
    W = pd.concat([ratings(book), spline(book.win_chance, CHANCE_KNOTS, "win_chance"), np.log1p(book.earlier_games),
                   book[["legal_moves", "captures_checks", "material", "opponent_clock_left"]]], axis=1)
    clock = (book.clock_left * 10).rename("clock")  # per DELTA
    effects.append(effect(population, "book_depth_iv", book, *iv(book.y, clock, book.book_moves, W, book.player)[:2]))
    fit = Within(pd.concat([clock, W], axis=1), book.player).fit(book.y)
    effects.append(effect(population, "book_depth_regression", book, *linear(fit, pd.Series({"clock": 1.0}))))

    late = repeated(sides[sides.lost_before_start.between(-0.01, 0.4)])
    m = Within(pd.concat([(late.lost_before_start * 10).rename("late"), ratings(late)], axis=1), late.player)
    for outcome, name in (("y", "late_start_score"), ("clock_left", "late_start_clock_left")):
        effects.append(effect(population, name, late, *linear(m.fit(late[outcome]), pd.Series({"late": 1.0}))))

    pairs = sides[sides.time_control.isin(["3600+30", "5400+30"])].copy()
    pairs["shorter"] = (pairs.time_control == "3600+30").astype(float)
    pairs = pairs[pairs.groupby("player").shorter.transform("nunique") == 2].reset_index(drop=True)
    m = Within(pd.concat([pairs.shorter, ratings(pairs)], axis=1), pairs.player)
    for outcome in ("time_trouble", "result_changing_error"):
        fit = m.fit(pairs[outcome].astype(float))
        effects.append(effect(population, f"{outcome}_60_30", pairs, *linear(fit, pd.Series({"shorter": 1.0})),
                              pairs[outcome][pairs.shorter == 0].mean()))
    return effects


def otb():
    sides = pd.concat([pd.read_parquet(f) for f in sorted((IN / "otb").glob("*.parquet"))], ignore_index=True)
    sides = prepare(sides.drop_duplicates(["key", "color"]))  # a game relayed several times: its first relay
    sides["time_control"] = (sides.base.astype(str) + "+" + sides.increment.astype(str)
                             + np.where(sides.extra_time.fillna(False), "+40", ""))
    model = repeated(sides[sides.win_chance.notna() & (sides.early_evals >= 0.9 * C)])
    controls = repeated(sides[sides.time_control.map(sides.time_control.value_counts()) >= 2000])
    rows, effects, curve = value("otb_classical", model, sides, controls, "time_trouble")
    return rows, effects + natural_experiments(sides), curve


def online(speed):
    sides = pd.read_parquet(IN / "online", filters=[("speed", "==", speed)],
                            columns=["key", "color", "player", "elo", "opponent_elo", "score", "base", "increment",
                                     "budget", "clock_left", "opponent_clock_left", "minutes_used", "early_error",
                                     "early_evals", "error", "opponent_error", "evals", "win_chance", "volatility",
                                     "legal_moves", "captures_checks", "material", "time_trouble", "hour",
                                     "lost_on_time"])
    sides = prepare(sides.merge(pd.read_parquet(IN / "stockfish"), on=["key", "color"], how="left"))
    sides["has_evals"] = sides.evals >= 0.95
    sides["win_chance"] = sides.win_chance.where(sides.has_evals, win_chance(sides.cp))
    time_control = sides.base.astype(str) + "+" + sides.increment.astype(str)
    controls = repeated(sides[time_control.isin(ONLINE_CONTROLS[speed]) & sides.has_evals
                              & (sides.early_evals >= 0.9 * C)])
    evaluated = repeated(sides[sides.has_evals])
    model = repeated(sides.dropna(subset=["win_chance"]))
    del sides, time_control  # memory: the design of model G is large
    rows, effects, _ = value(f"online_{speed}", model, evaluated, controls, "lost_on_time")
    return rows, effects


if __name__ == "__main__":
    rows, effects, curve = otb()
    for speed in ("blitz", "rapid"):
        more_rows, more_effects = online(speed)
        rows, effects = rows + more_rows, effects + more_effects
    for name, table in (("value_curve", curve), ("value", rows), ("effects", effects)):
        pd.DataFrame(table).to_csv(RESULTS / f"{name}.csv", index=False, float_format="%.6g")
