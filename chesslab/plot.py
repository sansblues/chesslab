"""Chart style: blue for what matters, grey for the rest, as few words as possible."""
import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

BLUE = "#2a78d6"
GREY = "#b4b2a9"
INK = "#2b2b2b"
MUTED = "#6b6a66"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 10,
    "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#d6d5ce", "axes.linewidth": 0.8, "axes.grid": False,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "xtick.major.size": 0, "ytick.major.size": 0, "lines.linewidth": 2, "svg.fonttype": "none",
    "svg.hashsalt": "chesslab",
})


def figure(unit: str, size=(6.4, 3.2)):
    """A figure with one axes; the unit of the y-axis sits above it, where it is read first."""
    fig, ax = plt.subplots(figsize=size, layout="constrained")
    ax.set_title(unit, loc="left", fontsize=10, color=MUTED, pad=10)
    return fig, ax


def label(ax, text, xy, color=MUTED, offset=(6, 0), **kw):
    """A direct label next to a point, instead of a legend."""
    ax.annotate(text, xy, xytext=offset, textcoords="offset points", va="center", color=color, **kw)


def save(fig, path):
    """Write the chart as an SVG file that is the same on every run."""
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
