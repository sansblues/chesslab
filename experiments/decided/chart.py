"""Chart the decisive points lost by cause and rating band. Reads results/points_lost.csv; writes decided.svg."""
from pathlib import Path

import numpy as np
import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
CAUSES = {"clock": ("clock", plot.BLUE), "opening_middlegame": ("opening and middlegame mistakes", plot.GREY),
          "endgame": ("endgame mistakes", plot.DARK_GREY),
          "resign_draw_other": ("resign, draw, other", plot.GREY + "80")}  # half-transparent: a lighter grey

lost = pd.read_csv(HERE / "results" / "points_lost.csv")
lost[list(CAUSES)] *= 100
online = lost.source == "online"
x = np.where(online, np.arange(len(lost)), np.arange(len(lost)) + 1)  # a gap between the two groups

fig, ax = plot.figure("The clock's share of decisive points lost grows with rating",
                      "Points lost per 100 games a player plays. Clock: lost on time, or a mistake in time trouble")
bottom = np.zeros(len(lost))
for cause, (label, color) in CAUSES.items():
    ax.bar(x, lost[cause], 0.6, bottom=bottom, color=color, label=label, edgecolor=plot.SURFACE, linewidth=0.5)
    bottom += lost[cause]
for xi, top, clock in zip(x, bottom, lost.clock):
    ax.annotate(f"{clock / top:.0%}", (xi, top), xytext=(0, 3), textcoords="offset points", ha="center",
                color=plot.BLUE, fontsize=8)
ax.set_xticks(x, lost.band.str.replace("-", "–\n"), fontsize=8)
for group, name in ((online, "Online (Lichess, all speeds)"), (~online, "Over the board (classical, FIDE rating)")):
    ax.annotate(name, (x[group].mean(), 0), xycoords=("data", "axes fraction"), xytext=(0, -34),
                textcoords="offset points", ha="center", color=plot.MUTED)
ax.set_ylim(0, 40)
ax.legend(loc="upper center", ncol=4, fontsize=8, handlelength=1, labelcolor=plot.MUTED)
plot.save(fig, HERE / "decided.svg")
