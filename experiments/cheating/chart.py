"""Read results/cherry_picking.csv; write cheating.svg."""
from pathlib import Path

import pandas as pd
from matplotlib.ticker import FuncFormatter

from chesslab import plot

HERE = Path(__file__).parent
table = pd.read_csv(HERE / "results" / "cherry_picking.csv")
last = table.iloc[-1]

fig, ax = plot.figure(f"Search {last.games:,.0f} games: {last.flagged:.0%} of honest players look like cheaters",
                      "Share of honest players whose best 5-game run passes a 1-in-10,000 test (simulated)")
ax.plot(table.games, table.flagged, color=plot.BLUE, marker="o", markersize=4)
for _, row in table[table.games.isin([1000, 10000])].iterrows():
    ax.annotate(f"{row.flagged:.0%}", (row.games, row.flagged), xytext=(-8, 6), textcoords="offset points",
                ha="right", color=plot.BLUE, fontweight="bold")
ax.annotate("A run chosen in advance\npasses in 1 case in 10,000", (last.games, 0), xytext=(0, 8),
            textcoords="offset points", ha="right", color=plot.DARK_GREY)
ax.set_xscale("log")
ax.minorticks_off()
ax.set_xticks([10, 100, 1000, 10000], ["10", "100", "1,000", "10,000"])
ax.set_ylim(0, 0.7)
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))
ax.set_xlabel("games played")
plot.save(fig, HERE / "cheating.svg")
