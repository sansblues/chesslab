"""Chart the clock's share of decisive points lost, by rating. Reads results/points_lost.csv; writes decided.svg."""
from pathlib import Path

import pandas as pd
from matplotlib.ticker import PercentFormatter

from chesslab import plot

HERE = Path(__file__).parent
CAUSES = ["clock", "opening_middlegame", "endgame", "resign_draw_other"]


def middle(band):
    """The rating a band stands for: '<1200' -> 1050, '1200-1499' -> 1350, '2400+' -> 2550."""
    if band.startswith("<"):
        return int(band[1:]) - 150
    if band.endswith("+"):
        return int(band[:-1]) + 150
    low, high = band.split("-")
    return (int(low) + int(high) + 1) / 2


lost = pd.read_csv(HERE / "results" / "points_lost.csv")
lost["rating"] = lost.band.map(middle)
lost["share"] = lost.clock / lost[CAUSES].sum(axis=1)

fig, ax = plot.figure("share of decisive points lost to the clock")
for source, name, color in (("online", "online", plot.GREY), ("otb", "over the board", plot.BLUE)):
    d = lost[lost.source == source]
    ax.plot(d.rating, d.share, color=color, marker="o", markersize=4)
    plot.label(ax, f"{name}", (d.rating.iloc[-1], d.share.iloc[-1]), color=color)
ax.set(xlim=(950, 2900), ylim=(0, 0.6), xticks=[1200, 1600, 2000, 2400], yticks=[0, 0.2, 0.4, 0.6])
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.set_xlabel("rating")
plot.save(fig, HERE / "decided.svg")
