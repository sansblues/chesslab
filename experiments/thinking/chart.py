"""Chart next year's rating change by time allocation and by error. Reads results/rating_change_by_decile.csv and
results/rating_change.csv; writes thinking.svg."""
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
deciles = pd.read_csv(HERE / "results" / "rating_change_by_decile.csv")
slope = pd.read_csv(HERE / "results" / "rating_change.csv").set_index("measure").elo_per_sd

fig, ax = plot.figure("rating change next year (Elo)")
ax.axhline(0, color=plot.GREY, linewidth=0.8, zorder=0)
for measure, name, color in (("error", "errors", plot.GREY), ("allocation_quality", "time allocation", plot.BLUE)):
    d = deciles[deciles.measure == measure]
    x = d.measure_sd.agg(["min", "max"])
    ax.scatter(d.measure_sd, d.rating_change, s=16, color=color, zorder=3)
    ax.plot(x, slope[measure] * x, color=color, linewidth=1.5)
    plot.label(ax, name, (x["max"], slope[measure] * x["max"]), color=color)
ax.set_xlim(right=ax.get_xlim()[1] + 0.8)
ax.set_xlabel("standard deviations from the average player")
plot.save(fig, HERE / "thinking.svg")
