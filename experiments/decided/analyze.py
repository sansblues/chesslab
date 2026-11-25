"""Find the move or the decision that settled each game, and the blunders around it.

Reads data/decided/ (extract.py). Writes results/points_lost.csv, decided.csv, blunders.csv,
punished.csv, resignations.csv and tablebase_resignations.csv.
"""
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from chesslab import DATA

IN = DATA / "decided"
RESULTS = Path(__file__).parent / "results"
CUTS = {"online": [1200, 1500, 1800, 2100, 2400], "otb": [1800, 2000, 2200, 2400]}
WON = 300  # centipawns: a position is won, drawn or lost at this margin
BLUNDER = 0.3  # a fall in the mover's winning chances, Lichess's definition
POPULATIONS = [("online", "blitz"), ("otb", "classical")]  # of the blunder tables


def band(elo, source):
    """Rating band; online bands for Lichess ratings, FIDE bands over the board."""
    out = pd.Series(None, index=elo.index, dtype=object)
    for name, cuts in CUTS.items():
        labels = np.array([f"<{cuts[0]}"] + [f"{a}-{b - 1}" for a, b in itertools.pairwise(cuts)] + [f"{cuts[-1]}+"])
        rows = (source == name) & elo.notna()
        out[rows] = labels[np.searchsorted(cuts, elo[rows], side="right")]
    return out


def winning_chances(cp):
    """Lichess's winning chances, -1..1, for the side whose value is cp."""
    return 2 / (1 + np.exp(-0.00368208 * np.clip(cp, -1000, 1000))) - 1


def load_games():
    """Every game once: online games of all speeds, over-the-board classical games (first relay)."""
    g = pd.concat([pd.read_parquet(p).assign(file=p.name.split(".")[0]) for p in sorted(IN.glob("*.games.parquet"))],
                  ignore_index=True)
    g["source"] = np.where(g.file.str.startswith("lichess"), "online", "otb")
    otb = g.source == "otb"
    g = g[~otb | (~g.key.duplicated() & (g.speed == "classical"))].copy()
    g["white_band"] = band(g.white_elo, g.source)
    g["black_band"] = band(g.black_elo, g.source)
    g["band"] = band((g.white_elo + g.black_elo) / 2, g.source)
    # Post-stratify the online games with evals (someone asked for an analysis) to all online games:
    # cells of speed x average band x how the game ended x length.
    online = g[g.source == "online"]
    cells = [online.speed, online.band.fillna("?"), online.end, pd.cut(online.plies, [0, 40, 80, 120, np.inf])]
    by_cell = online.groupby(cells, observed=True).has_eval
    g["weight"] = 1.0
    g.loc[online.index, "weight"] = (by_cell.transform("size") / by_cell.transform("sum")
                                     * online.has_eval.sum() / len(online))
    return g[g.final_fen.notna()]


def file_moves(path, games):
    """The plies of one file, with game data and the values for the mover."""
    p = pd.read_parquet(path).merge(games, on="game")
    white = p.ply % 2 == 0
    p["side"] = np.where(white, 1, -1)
    p["band"] = np.where(white, p.white_band, p.black_band)
    p["phase"] = np.select([p.material <= 26, p.ply < 30], ["endgame", "opening"], "middlegame")
    before = p.groupby("game").value.shift().where(p.ply > 0, 20)
    p["wc0"] = winning_chances(p.side * before)
    p["wc1"] = winning_chances(p.side * p.value)
    p["fall"] = p.wc0 - p.wc1
    p["blunder"] = p.fall >= BLUNDER
    p["class"] = np.sign(p.value).where(p.value.abs() >= WON, 0).where(p.value.notna())
    return p


def decide(p):
    """Per game, the moment the result was settled (classes are White's: 1 won, 0 drawn, -1 lost).
    offboard: the final position's class is not the result (a resignation, a loss on time, a draw);
    error: the last move after which the class was the result and stayed so, if it made the mover's
    class worse; noise: such a move that did not; never: a draw never in doubt."""
    p = p.assign(final=2 * p.result - 1, after=p.groupby("game")["class"].ffill().fillna(0))
    p["before"] = p.groupby("game").after.shift().fillna(0)
    last = p.groupby("game").tail(1).set_index("game")
    d = p[p.before != p.final].groupby("game").tail(1).set_index("game").reindex(last.index)
    out = last[["source", "speed", "weight", "white_band", "black_band", "end"]].copy()
    offboard = last.after != last.final
    error = ~offboard & (d.side * d.after < d.side * d.before)
    out["kind"] = np.select([offboard, d.before.isna(), error], ["offboard", "never", "error"], "noise")
    out["loser"] = np.select([offboard, error], [np.where(last.final < last.after, 1, -1), d.side], 0)
    out["points"] = np.select([offboard, error], [(last.final - last.after).abs(), (last.final - d.before).abs()], 0) / 2
    out["cause"] = np.select(
        [offboard & (last.end == "flag"), offboard, d.clock < 0.1, (d.pieces <= 6) | (d.material <= 26)],
        ["clock", "resign_draw_other", "clock", "endgame"], "opening_middlegame")
    out["tablebase"] = error & (d.pieces <= 6)
    return out.reset_index()


def blunder_counts(p):
    """Moves and blunders by stratum and by what happened just before, for the blunder tables."""
    b = p[p.fall.notna() & (p.ply >= 2)
          & pd.Series(list(zip(p.source, p.speed)), index=p.index).isin(POPULATIONS)]
    previous = p.groupby("game").blunder.shift(fill_value=False)[b.index]
    own = p.groupby("game").blunder.shift(2, fill_value=False)[b.index]
    clock = np.select([b.clock.isna(), b.clock < 0.05, b.clock < 0.1, b.clock < 0.2, b.clock < 0.5],
                      ["n", "a", "b", "c", "d"], "e")
    keys = pd.DataFrame({"source": b.source, "speed": b.speed, "band": b.band.fillna("?"),
                         "chances": np.minimum(9, np.floor((b.wc0 + 1) * 5)), "clock": clock, "phase": b.phase,
                         "after_opponent": previous & ~own, "after_own": own & (b.ply >= 4)})
    return b.groupby([keys[c] for c in keys]).blunder.agg(moves="size", blunders="sum").reset_index()


def punish_counts(p):
    """Replies to an opponent's blunder that give back more than half of what it gained."""
    gain = p.groupby("game").fall.shift()
    start = -p.groupby("game").wc0.shift() + gain / 2  # the mover's chances before the blunder, plus half the gain
    b = p[p.fall.notna() & (p.ply >= 2)]
    gain, start = gain[b.index], start[b.index]
    later = b.groupby("game").wc1
    worst = np.fmin(b.wc1, np.fmin(later.shift(-2), later.shift(-4)))
    r = b.assign(missed=b.wc1 < start, missed_within_3=worst < start)[gain >= BLUNDER]
    r = r[pd.Series(list(zip(r.source, r.speed)), index=r.index).isin(POPULATIONS)]
    return r.groupby(["source", "speed", "band"]).agg(replies=("missed", "size"), missed=("missed", "sum"),
                                                      missed_within_3=("missed_within_3", "sum")).reset_index()


def points_lost(g, d):
    """Decisive points lost per player-game by cause and the loser's band (weighted online)."""
    rows = []
    for source in ("online", "otb"):
        games, losses = g[g.source == source], d[(d.source == source) & (d.loser != 0)]
        loser_band = np.where(losses.loser == 1, losses.white_band, losses.black_band)
        lost = (losses.weight * losses.points).groupby([loser_band, losses.cause]).sum().unstack(fill_value=0)
        for b in sorted(set(games.white_band.dropna()) | set(games.black_band.dropna()), key=_band_order):
            player_games = (games.white_band == b).sum() + (games.black_band == b).sum()
            weighted = (games.weight * ((games.white_band == b).astype(int) + (games.black_band == b))).sum()
            rows.append({"source": source, "band": b, "player_games": player_games,
                         **(lost.loc[b] / weighted).to_dict()})
    columns = ["source", "band", "player_games", "clock", "opening_middlegame", "endgame", "resign_draw_other"]
    return pd.DataFrame(rows)[columns]


def _band_order(b):
    return int(b.strip("<+").split("-")[0]) - (b[0] == "<")


def main():
    g = load_games()
    decided, blunders, punished = [], [], []
    for path in sorted(IN.glob("*.plies.parquet")):
        columns = ["game", "source", "speed", "result", "end", "weight", "white_band", "black_band"]
        p = file_moves(path, g.loc[g.file == path.name.split(".")[0], columns])
        decided.append(decide(p))
        blunders.append(blunder_counts(p))
        punished.append(punish_counts(p))
        print(path.name, len(p), flush=True)
    d = pd.concat(decided)
    RESULTS.mkdir(exist_ok=True)
    write = lambda df, name: df.to_csv(RESULTS / name, index=False, float_format="%.6g")

    write(points_lost(g, d), "points_lost.csv")

    rows = []  # by speed: shares of the sample; online, all speeds: weighted as in points_lost.csv
    for (source, speed), x in itertools.chain(d.groupby(["source", "speed"]), [(("online", "all"), d[d.source == "online"])]):
        w = x.weight if speed == "all" else None
        rows.append({"source": source, "speed": speed, "games": len(x),
                     "offboard": np.average(x.kind == "offboard", weights=w),
                     "tablebase": np.average(x.tablebase, weights=w)})
    write(pd.DataFrame(rows), "decided.csv")

    b = pd.concat(blunders)
    keys = ["source", "speed", "band", "chances", "clock", "phase"]
    b = b.groupby(keys + ["after_opponent", "after_own"], as_index=False)[["moves", "blunders"]].sum()
    rate = b.groupby(keys).blunders.transform("sum") / b.groupby(keys).moves.transform("sum")
    b["expected"] = b.moves * rate
    rows = []
    for situation in ("after_opponent", "after_own"):
        for (source, speed), x in b[b[situation]].groupby(["source", "speed"]):
            rows.append({"source": source, "speed": speed, "situation": situation, "moves": x.moves.sum(),
                         "blunders": x.blunders.sum(), "ratio": x.blunders.sum() / x.expected.sum()})
    write(pd.DataFrame(rows), "blunders.csv")

    r = pd.concat(punished).groupby(["source", "speed", "band"], as_index=False).sum()
    r[["missed", "missed_within_3"]] = r[["missed", "missed_within_3"]].div(r.replies, axis=0)
    write(r.sort_values(["source", "speed", "band"], key=lambda c: c.map(_band_order) if c.name == "band" else c),
          "punished.csv")

    resigned = g[(g.source == "online") & (g.end == "resign")].copy()
    resigner = np.where(resigned.result == 1, -1, 1)
    resigned["value"] = resigner * resigned.final_value
    known = resigned[resigned.value.notna()]
    rows = [{"speed": speed, "resignations": len(x), "not_lost": (x.value > -WON).mean()}
            for speed, x in itertools.chain(known.groupby("speed"), [("all", known)])]
    write(pd.DataFrame(rows), "resignations.csv")

    drawn = resigned[resigned.final_tablebase.astype(bool) & (resigned.value >= 0)]
    write(pd.DataFrame({"url": drawn.url, "speed": drawn.speed,
                        "resigner_elo": np.where(drawn.result == 1, drawn.black_elo, drawn.white_elo),
                        "resigner_clock": np.where(drawn.result == 1, drawn.black_clock, drawn.white_clock),
                        "tablebase": np.where(drawn.value > 0, "win", "draw"), "fen": drawn.final_fen}
                       ).sort_values("url"), "tablebase_resignations.csv")


if __name__ == "__main__":
    main()
