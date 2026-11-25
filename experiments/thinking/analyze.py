"""The pre-registered test and the checks that explain its result.
Reads data/thinking/ (positions, game_sides, stockfish) and the FIDE lists jul24, jul25, jul26.
Writes results/*.csv."""
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from chesslab import DATA, samples
from chesslab.games import win_chance

RESULTS = Path(__file__).parent / "results"
CONTROLS = ("rating + I(rating**2) + bs(age, knots=(14,18,25,40,60), degree=1) + C(k) + C(sex) + z_error"
            " + z_over + log_games + z_mean_log_time + z_time_trouble + prior + prior_missing")


def spearman(frame, x, y, by):
    """Spearman correlation of columns x and y within each group (average ranks for ties)."""
    r = frame.groupby(by)[[x, y]].rank()
    r = r - r.groupby([frame[c] for c in by]).transform("mean")
    s = pd.DataFrame({"xy": r[x] * r[y], "xx": r[x] ** 2, "yy": r[y] ** 2}).groupby([frame[c] for c in by]).sum()
    return s.xy / np.sqrt(s.xx * s.yy)


def spearman_brown(r):
    """Reliability of a measure twice as long."""
    return 2 * r / (1 + r)


def standardize(s):
    return (s - s.mean()) / s.std()


def coefficient(model, term):
    low, high = model.conf_int().loc[term]
    return {"estimate": model.params[term], "low": low, "high": high, "p": model.pvalues[term]}


def save(table, name):
    pd.DataFrame(table).to_csv(RESULTS / f"{name}.csv", index=False, float_format="%.6g")


def positions():
    """Every analysed position not yet decided (|deep eval| <= 300) with its value of thinking."""
    S = pd.concat(pd.read_parquet(f, columns=["fen", "best_cp", "depth4_cp", "depth8_cp"])
                  for f in sorted((DATA / "thinking" / "stockfish").glob("chunk_*.parquet")))
    P = pd.read_parquet(DATA / "thinking" / "positions.parquet").merge(S, on="fen")
    analysed = len(P)
    P = P[P.best_cp.abs() <= 300].copy()
    P["voc"] = np.maximum(0, win_chance(P.best_cp) - win_chance(P.depth4_cp))  # what a quick (depth-4) look costs
    P["voc8"] = np.maximum(0, win_chance(P.best_cp) - win_chance(P.depth8_cp))
    P["log_time"] = np.log1p(P.think_time)
    P["paced_time"] = P.log_time - P.groupby(["fide_id", "game"]).log_time.transform("mean")
    P["error"] = np.maximum(0, win_chance(P.eval_before) - win_chance(P.eval_after))  # stored Lichess evals
    return P, analysed


def players(P, G):
    """Allocation quality (AQ), its split halves, and the controls of each player."""
    P["half"] = P.groupby("fide_id").game.rank(method="dense") % 2
    halves = P.groupby(["fide_id", "half"]).agg(mean_log_time=("log_time", "mean"),
                                                time_variability=("paced_time", "std"))
    halves["allocation_quality"] = spearman(P, "voc", "paced_time", ["fide_id", "half"])
    X = G.groupby("fide_id").agg(error=("error", "mean"), over=("over", "mean"),
                                 games=("game", "size"), mean_log_time=("mean_log_time", "mean"),
                                 time_trouble=("time_trouble", "mean"))
    X["aq"] = spearman(P, "voc", "paced_time", ["fide_id"])
    fide = {m: samples.fide(m).set_index("id").astype({"rating": float, "birth_year": float, "k": float})
            for m in ("jul24", "jul25", "jul26")}
    ids = X.index.to_series()
    listed = {m: ids.map(f.rating) for m, f in fide.items()}
    birth = ids.map(fide["jul25"].birth_year)
    X["age"] = (2025 - birth).where(birth > 1900)
    X["k"] = ids.map(fide["jul25"].k).astype("Int64").astype(str)
    X["sex"] = ids.map(fide["jul25"].sex)
    X["rating"] = (listed["jul25"] - 2000) / 100
    X["rating_change"] = listed["jul26"] - listed["jul25"]
    X["prior"] = listed["jul25"] - listed["jul24"]
    X["prior_missing"] = X.prior.isna().astype(int)
    X["prior"] = X.prior.fillna(0)
    X = X.dropna(subset=["rating_change", "aq", "age", "error", "over", "rating"])
    X = X[X.age.between(5, 95)].copy()
    for c in ("aq", "error", "over", "mean_log_time", "time_trouble"):
        X["z_" + c] = standardize(X[c])
    X["log_games"] = np.log(X.games)
    return X.reset_index(), halves.unstack("half")


def rating_change(P, X):
    """The primary model (OLS, HC3) and its permutation null; the positive control (error)."""
    model = smf.ols("rating_change ~ z_aq + " + CONTROLS, X).fit(cov_type="HC3")
    # null: shuffle the paced times within each game-side, game-sides in sorted order (seed 5, 200 times), refit
    rng = np.random.default_rng(5)
    Q = P[P.fide_id.isin(X.fide_id)].sort_values(["fide_id", "game"], kind="stable")
    bounds = np.r_[0, Q.groupby(["fide_id", "game"]).size().cumsum().values]
    paced, null = Q.paced_time.values, []
    for _ in range(200):
        Q["shuffled"] = np.concatenate([rng.permutation(paced[a:b]) for a, b in itertools.pairwise(bounds)])
        X["z_shuffled"] = standardize(X.fide_id.map(spearman(Q, "voc", "shuffled", ["fide_id"])))
        null.append(smf.ols("rating_change ~ z_shuffled + " + CONTROLS, X).fit().params["z_shuffled"])
    rows = []
    for measure, term in (("allocation_quality", "z_aq"), ("error", "z_error")):
        c = coefficient(model, term)
        rows.append({"measure": measure, "elo_per_sd": c["estimate"], "elo_per_sd_low": c["low"],
                     "elo_per_sd_high": c["high"], "p": c["p"], "players": int(model.nobs)})
    rows[0]["permutation_p"] = np.mean(np.abs(null) >= abs(rows[0]["elo_per_sd"]))
    save(rows, "rating_change")
    return model


def reliability(halves, high):
    """Split-half reliability (odd vs even games, 3 vs 3), and the largest true effect per SD of true
    AQ that the upper CI bound of the primary model allows: high / sqrt(reliability)."""
    rows = []
    for measure in ("allocation_quality", "mean_log_time", "time_variability"):
        a, b = halves[measure][0], halves[measure][1]
        r = a.corr(b)
        rows.append({"measure": measure, "split_half": r, "spearman_brown": spearman_brown(r),
                         "games_for_0_7": 3 * 0.7 * (1 - r) / (0.3 * r)})  # Spearman-Brown, from 3 games
    ok = halves.allocation_quality.notna().all(axis=1)
    a, b = halves.allocation_quality[0][ok].values, halves.allocation_quality[1][ok].values
    rng = np.random.default_rng(1)
    boot = [np.corrcoef(a[i], b[i])[0, 1] for i in (rng.integers(0, len(a), len(a)) for _ in range(1000))]
    rows[0]["split_half_low"], rows[0]["split_half_high"] = np.percentile(boot, [2.5, 97.5])
    save(rows, "reliability")
    bound = [{"reliability": case, "spearman_brown": spearman_brown(r)} for case, r in
             (("estimate", rows[0]["split_half"]), ("ci_low", rows[0]["split_half_low"]))]
    save([dict(b, elo_per_true_sd_max=high / np.sqrt(b["spearman_brown"])) for b in bound], "effect_bound")


def by_decile(model):
    """Rating change by decile of AQ and of error, both adjusted for every other term of the model
    (Frisch-Waugh: the slope through the deciles is the coefficient)."""
    exog = pd.DataFrame(model.model.exog, columns=model.model.exog_names)
    rows = []
    for measure, term in (("allocation_quality", "z_aq"), ("error", "z_error")):
        others = exog.drop(columns=term).values
        x, y = (v - others @ np.linalg.lstsq(others, v, rcond=None)[0] for v in (exog[term].values, model.model.endog))
        for decile, d in pd.DataFrame({"x": x, "y": y}).groupby(pd.qcut(x, 10, labels=False) + 1):
            rows.append({"measure": measure, "decile": decile, "players": len(d), "measure_sd": d.x.mean(),
                             "rating_change": d.y.mean()})
    save(rows, "rating_change_by_decile")


def within_game(P, G):
    """Within a player: are the games with better allocation the better games? (score minus the
    Elo-expected score; game-sides with >= 15 positions; player-demeaned; clustered by player)."""
    by = ["fide_id", "game"]
    W = P.merge(G[by + ["over", "mean_log_time"]], on=by)
    S = W.groupby(by).agg(positions=("voc", "size"), over=("over", "first"),
                          mean_log_time=("mean_log_time", "first"), mean_voc=("voc", "mean"))
    S["aq"] = spearman(W, "voc", "paced_time", by)
    S = S[S.positions >= 15].dropna(subset=["aq", "over"]).reset_index()
    for c in ("aq", "over", "mean_log_time", "mean_voc"):
        S[c + "_within"] = S[c] - S.groupby("fide_id")[c].transform("mean")
    S["z_aq_within"] = S.aq_within / S.aq.std()
    model = smf.ols("over_within ~ z_aq_within + mean_log_time_within + mean_voc_within", S).fit(
        cov_type="cluster", cov_kwds={"groups": S.fide_id})
    c = coefficient(model, "z_aq_within")
    save([{"games": len(S), "score_per_sd": c["estimate"], "score_per_sd_low": c["low"], "score_per_sd_high": c["high"],
               "p": c["p"]}], "within_game")


def critical_moves(P):
    """Is time worth more where the VOC is high? Critical: top 20% VOC; low clock: < 10 min before
    the move; fast: < 30 s. Error: win probability lost, from the stored evals (mates excluded)."""
    M = P.dropna(subset=["eval_before", "eval_after"])
    M = M[(M.eval_before.abs() < 9000) & (M.eval_after.abs() < 9000)].copy()
    M["critical"] = (M.voc >= M.voc.quantile(0.8)).astype(int)
    M["low_clock"] = (M.clock_before < 600).astype(int)
    M["fast"] = (M.think_time < 30).astype(int)
    M["critical_low_clock"] = M.critical * M.low_clock
    for c in ("error", "critical", "low_clock", "critical_low_clock"):
        M[c + "_within"] = M[c] - M.groupby("fide_id")[c].transform("mean")
    M["phase"] = pd.cut(M.ply // 2 + 1, [8, 15, 20, 25, 30, 35, 41]).astype(str)
    model = smf.ols("error_within ~ critical_within + low_clock_within + critical_low_clock_within + C(phase)", M).fit(
        cov_type="cluster", cov_kwds={"groups": M.fide_id})
    save([dict(term=t, **coefficient(model, t + "_within")) for t in ("critical", "low_clock", "critical_low_clock")],
         "low_clock")
    T = M.groupby(["critical", "fast"]).error.agg(positions="size", error="mean", total="sum").reset_index()
    T["error_share"] = T.pop("total") / M.error.sum()
    save(T, "critical_moves")


def main():
    P, analysed = positions()
    G = pd.read_parquet(DATA / "thinking" / "game_sides.parquet")
    G["over"] = G.score - 1 / (1 + 10 ** ((G.opponent_elo - G.elo) / 400))
    X, halves = players(P, G)
    save([{"eligible_players": G.fide_id.nunique(), "players": P.fide_id.nunique(),
               "game_sides": len(P.groupby(["fide_id", "game"])), "positions_analysed": analysed, "positions": len(P),
               "model_players": len(X)}], "sample")
    model = rating_change(P, X)
    reliability(halves, coefficient(model, "z_aq")["high"])
    by_decile(model)
    within_game(P, G)
    critical_moves(P)
    rho = P[["voc", "voc8", "error"]].corr("spearman")
    save([{"proxy": "voc_depth8", "spearman": rho.at["voc", "voc8"]},
          {"proxy": "error", "spearman": rho.at["voc", "error"]}], "voc_agreement")
    P["band"] = pd.cut(P.elo, [0, 1600, 1800, 2000, 2200, 2400, 3000],
                       labels=["<=1600", "1601-1800", "1801-2000", "2001-2200", "2201-2400", ">2400"])
    bands = P.groupby("band", observed=True).size().rename("positions").to_frame()
    bands["spearman"] = spearman(P, "voc", "paced_time", ["band"])
    save(bands.reset_index(), "time_voc_by_rating")


if __name__ == "__main__":
    main()
