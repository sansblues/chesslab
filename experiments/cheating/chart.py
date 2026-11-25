"""Chart the cherry-picking trap. Reads results/cherry_picking.csv; writes cheating.svg."""
from pathlib import Path

import pandas as pd

from chesslab import plot

HERE = Path(__file__).parent
table = pd.read_csv(HERE / "results" / "cherry_picking.csv")
points = list(zip(table.games, table.flagged * 100))
at = {games: i for i, (games, _) in enumerate(points)}
plot.save(HERE / "cheating.svg", [
    plot.Line(points, plot.BLUE, [(at[1000], f"{points[at[1000]][1]:.0f}%", "above"),
                                  (-1, f"{points[-1][1]:.0f}% look guilty", "end")]),
], ticks=[(10, "10"), (100, "100"), (1000, "1,000"), (10000, "10,000 games")], ymax=65, xlog=True)
