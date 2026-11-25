"""Chart the Elo that goes with 10% more clock at move 20. Reads results/value_curve.csv; writes clock.svg."""
from math import log10
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
curve = pd.read_csv(HERE / "results" / "value_curve.csv")
elo = [400 * log10((1 + 2 * g) / (1 - 2 * g)) for g in curve.gain]  # a score gain of g from 50%, in Elo
points = list(zip(curve.clock_left * 100, elo))
plot.save(HERE / "clock.svg", [
    plot.Line(points, plot.BLUE, [(0, f"+{points[0][1]:.0f} Elo", "above"), (-1, f"+{points[-1][1]:.0f} Elo", "end")]),
], ticks=[(10, "10%"), (30, "30%"), (60, "60% of the time left")], ymax=35)
