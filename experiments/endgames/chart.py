"""Chart the rule of five against perfect play. Reads results/rule_of_five_by_sum.csv; writes endgames.svg."""
from pathlib import Path

import pandas as pd
from matplotlib.ticker import PercentFormatter

from chesslab import plot

HERE = Path(__file__).parent
by_sum = pd.read_csv(HERE / "results" / "rule_of_five_by_sum.csv")
by_sum["sum"] = by_sum["sum"].clip(upper=7)
by_sum = by_sum.groupby("sum")[["positions", "white_wins"]].sum()
rate = by_sum.white_wins / by_sum.positions
labels = [str(s) if s < 7 else "7+" for s in by_sum.index]

fig, ax = plot.figure("White wins")
bars = ax.bar(labels, rate, width=0.6, color=[plot.BLUE if s == 5 else plot.GREY for s in by_sum.index])
ax.bar_label(bars, [f"{r:.0%}" for r in rate], padding=3, color=plot.MUTED)
ax.axvline(2.5, color=plot.GREY, linewidth=1, linestyle=(0, (2, 3)))
ax.text(2.4, 1.12, "rule says draw", ha="right", color=plot.MUTED)
ax.text(2.6, 1.12, "rule says win", ha="left", color=plot.MUTED)
ax.set(ylim=(0, 1.18), yticks=[0, 0.5, 1])
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.set_xlabel("pawn rank + files the king is cut off")
plot.save(fig, HERE / "endgames.svg")
