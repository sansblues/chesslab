"""Chart the cherry-picking trap. Reads results/cherry_picking.csv; writes cheating.svg."""
from pathlib import Path

import pandas as pd
from matplotlib.ticker import PercentFormatter

from chesslab import plot

HERE = Path(__file__).parent
table = pd.read_csv(HERE / "results" / "cherry_picking.csv")

fig, ax = plot.figure("honest players whose best run looks like 1-in-10,000 proof")
ax.plot(table.games, table.flagged, color=plot.BLUE, marker="o", markersize=4)
for _, row in table[table.games.isin([1000, 10000])].iterrows():
    plot.label(ax, f"{row.flagged:.0%}", (row.games, row.flagged), color=plot.BLUE, offset=(-8, 4), ha="right")
ax.set_xscale("log")
ax.minorticks_off()
ax.set(xticks=[10, 100, 1000, 10000], xticklabels=["10", "100", "1,000", "10,000"], ylim=(0, 0.7),
       yticks=[0, 0.2, 0.4, 0.6])
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.set_xlabel("games played")
plot.save(fig, HERE / "cheating.svg")
