"""Charts as plain SVG: the data and the few numbers that matter, nothing else."""
from dataclasses import dataclass, field
from math import log10

BLUE = "#2f81f7"
GREY = "#8c959f"  # both colours read on light and dark pages
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


@dataclass
class Line:
    points: list[tuple[float, float]]
    color: str = BLUE
    labels: list[tuple[int, str, str]] = field(default_factory=list)  # (point index, text, "end" | "above" | "below")


def save(path, lines, ticks, ymax, xlog=False, width=640, height=180):
    """Draw lines over a shared x-axis that shows only its tick labels."""
    left, right, top, bottom = 40, 150, 28, 32
    xs = [x for line in lines for x, _ in line.points] + [x for x, _ in ticks]
    scale = log10 if xlog else float
    x0, x1 = scale(min(xs)), scale(max(xs))

    def at(x, y):
        return (left + (scale(x) - x0) / (x1 - x0) * (width - left - right),
                height - bottom - y / ymax * (height - top - bottom))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" font-family="{FONT}" font-size="13">')
    out = [svg]
    for line in lines:
        points = " ".join(f"{px:.1f},{py:.1f}" for px, py in (at(x, y) for x, y in line.points))
        out.append(f'<polyline points="{points}" fill="none" stroke="{line.color}" stroke-width="2" '
                   'stroke-linejoin="round" stroke-linecap="round"/>')
        for index, text, side in line.labels:
            px, py = at(*line.points[index])
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{line.color}"/>')
            tx, ty, anchor = {"end": (px + 8, py + 4, "start"), "above": (px, py - 10, "middle"),
                              "below": (px, py + 20, "middle")}[side]
            if side != "end" and px < 100:  # near the left edge, a label starts at its point
                tx, anchor = px - 4, "start"
            out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" fill="{line.color}">{text}</text>')
    for x, text in ticks:
        out.append(f'<text x="{at(x, 0)[0]:.1f}" y="{height - 8}" text-anchor="middle" font-size="12" '
                   f'fill="{GREY}">{text}</text>')
    out.append("</svg>\n")
    path.write_text("\n".join(out))
