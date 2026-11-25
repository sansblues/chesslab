"""Chart what 10% more clock at move 20 goes with. Reads results/value_curve.csv; writes clock.svg."""
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
curve = pd.read_csv(HERE / "results" / "value_curve.csv")
points = list(zip(curve.clock_left * 100, curve.gain * 100))
plot.save(HERE / "clock.svg", [
    plot.Line(points, plot.BLUE, [(0, f"+{points[0][1]:.1f} points per 100 games", "above"),
                                  (-1, f"+{points[-1][1]:.1f}", "end")]),
], ticks=[(10, "10%"), (30, "30%"), (60, "60% of the clock left")], ymax=5)
