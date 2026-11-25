"""Chart the clock's share of the points lost, by rating. Reads results/points_lost.csv; writes decided.svg."""
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
CAUSES = ["clock", "opening_middlegame", "endgame", "resign_draw_other"]


def rating(band):
    """The rating a band stands for: '<1200' -> 1050, '1200-1499' -> 1350, '2400+' -> 2550."""
    if band.startswith("<"):
        return int(band[1:]) - 150
    if band.endswith("+"):
        return int(band[:-1]) + 150
    low, high = band.split("-")
    return (int(low) + int(high) + 1) / 2


lost = pd.read_csv(HERE / "results" / "points_lost.csv")
lost["share"] = lost.clock / lost[CAUSES].sum(axis=1) * 100
online, otb = ([(rating(r.band), r.share) for r in lost[lost.source == s].itertuples()] for s in ("online", "otb"))
plot.save(HERE / "decided.svg", [
    plot.Line(online, plot.GREY, [(0, f"{online[0][1]:.0f}%", "above"), (-1, f"{online[-1][1]:.0f}% online", "end")]),
    plot.Line(otb, plot.BLUE, [(0, f"{otb[0][1]:.0f}%", "below"),
                               (-1, f"{otb[-1][1]:.0f}% over the board", "end")]),
], ticks=[(1200, "1200"), (1600, "1600"), (2000, "2000"), (2400, "2400")], ymax=60)
