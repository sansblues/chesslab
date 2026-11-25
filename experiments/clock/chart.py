"""Chart what 10% more clock at move 20 goes with. Reads results/value_curve.csv and results/value.csv;
writes clock.svg."""
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
curve = pd.read_csv(HERE / "results" / "value_curve.csv")
otb = pd.read_csv(HERE / "results" / "value.csv").query("population == 'otb_classical'").set_index("group")
x = curve.clock_left * 100

fig, ax = plot.figure("points per 100 games, with 10% more clock")
ax.fill_between(x, curve.gain_low * 100, curve.gain_high * 100, color=plot.BLUE, alpha=0.15, linewidth=0)
ax.plot(x, curve.gain * 100, color=plot.BLUE, marker="o", markersize=4)
for group, name in (("habitually_short", "short of time"), ("all", "typical")):
    left = otb.median_clock_left[group] * 100
    ax.axvline(left, color=plot.GREY, linewidth=1, linestyle=(0, (2, 3)), zorder=0)
    plot.label(ax, name, (left, 4.6), offset=(4, 0))
ax.set(xlim=(8, 62), ylim=(0, 5), xticks=range(10, 70, 10), xticklabels=[f"{t}%" for t in range(10, 70, 10)])
ax.set_xlabel("clock left at move 20")
plot.save(fig, HERE / "clock.svg")
