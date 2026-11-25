"""The value curve of clock time at move 20. Reads results/value_curve.csv and results/value.csv; writes clock.svg."""
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
curve = pd.read_csv(HERE / "results" / "value_curve.csv")
otb = pd.read_csv(HERE / "results" / "value.csv").query("population == 'otb_classical'").set_index("group")

fig, ax = plot.figure("Extra clock at move 20 is worth most when little is left",
                      "Points per 100 games from 10% more of the budget (base + 40 × increment); 95% CI")
ax.fill_between(curve.clock_left * 100, curve.gain_low * 100, curve.gain_high * 100, color=plot.BLUE, alpha=0.15,
                linewidth=0)
ax.plot(curve.clock_left * 100, curve.gain * 100, color=plot.BLUE, marker="o", markersize=4)
top = curve.gain_high.max() * 100 * 1.1
for group, label in (("habitually_short", "habitually short"), ("all", "typical")):
    x = otb.median_clock_left[group] * 100
    ax.axvline(x, color=plot.GREY, linewidth=1, linestyle="--", zorder=0)
    ax.annotate(f"{label}:\nmedian {x:.0f}%", (x, top), xytext=(4, 0), textcoords="offset points", va="top",
                color=plot.MUTED, fontsize=9)
ax.set(xlim=(8, 62), ylim=(0, top), xticks=range(10, 70, 10), xticklabels=[f"{x}%" for x in range(10, 70, 10)])
ax.set_xlabel(f"Clock left after move 20 (share of the budget); {otb.game_sides['all']:,} classical OTB game-sides")
plot.save(fig, HERE / "clock.svg")
