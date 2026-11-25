"""The chart: rating change by decile of time-allocation quality and of error, with the fitted lines.
Reads results/rating_change_by_decile.csv and results/rating_change.csv. Writes thinking.svg."""
from pathlib import Path

import numpy as np
import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
D = pd.read_csv(HERE / "results" / "rating_change_by_decile.csv")
B = pd.read_csv(HERE / "results" / "rating_change.csv").set_index("measure")

fig, ax = plot.figure("Time allocation does not predict rating change; errors do",
                      f"FIDE rating change Jul 2025 to Jul 2026 (Elo) by decile; {B.players.iloc[0]:,} players, "
                      "controls held fixed")
for measure, color, label in (("error", plot.GREY, "Error"), ("allocation_quality", plot.BLUE, "Time allocation")):
    d, slope = D[D.measure == measure], B.at[measure, "elo_per_sd"]
    ax.scatter(d.measure_sd, d.rating_change, s=22, color=color, zorder=3)
    x = np.array([d.measure_sd.min(), d.measure_sd.max()])
    ax.plot(x, slope * x, color=color, linewidth=1.5)
    ax.annotate(f"{label}\n{slope:+.1f} Elo per SD".replace("-", "−"), (x[1], slope * x[1]), xytext=(8, 0),
                textcoords="offset points", va="center", color=plot.INK if color == plot.BLUE else plot.MUTED)
ax.axhline(0, color=plot.DARK_GREY, linewidth=0.8, zorder=1)
ax.set_xlabel("Measure, adjusted for the controls (SD)")
ax.set_xlim(right=ax.get_xlim()[1] + 0.9)
plot.save(fig, HERE / "thinking.svg")
