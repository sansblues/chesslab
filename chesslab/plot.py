"""The house style of the charts: quiet greys, one blue accent, a title that states the finding."""
import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

BLUE = "#2a78d6"  # the accent: the one thing the chart is about
GREY = "#b4b2a9"  # everything else
DARK_GREY = "#898781"  # a second grey, if one is needed
INK = "#0b0b0b"
MUTED = "#52514e"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 10,
    "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
    "axes.axisbelow": True, "xtick.major.size": 0, "ytick.major.size": 0,
    "axes.prop_cycle": matplotlib.cycler(color=[BLUE, GREY, DARK_GREY]),
    "lines.linewidth": 2, "legend.frameon": False, "svg.fonttype": "none", "svg.hashsalt": "chesslab",
})


def figure(title: str, subtitle: str = "", size=(7, 3.6)):
    """A figure with one axes. The title states the finding; the subtitle says what is plotted."""
    fig, ax = plt.subplots(figsize=size, layout="constrained")
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", pad=28 if subtitle else 12)
    ax.annotate(subtitle, (0, 1), xycoords="axes fraction", xytext=(0, 10), textcoords="offset points", color=MUTED)
    return fig, ax


def save(fig, path):
    """Write the chart as an SVG file that is the same on every run."""
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
