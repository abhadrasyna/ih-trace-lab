"""Canvas charts: a figure-sized axes measured in inches (y down), so text, bars and corners are placed exactly.

The "story" renderers (``rate_bars``, ``columns``, ``trend``, ``composition``) draw on a ``Canvas``. Every one shares the
same frame: finding title, one-line measure subtitle, content on the single left edge, one-line scope footer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.lib.charts.errors import ChartError
from src.lib.charts.fig import BASE_HEIGHT, BASE_WIDTH, new_figure, render_png
from src.lib.charts.shapes import add_rounded_bar
from src.lib.charts.theme import ChartTheme, chart_font_family
from src.lib.charts.title import LEFT_EDGE, draw_footer, draw_title

WIDTH = BASE_WIDTH
HEIGHT = BASE_HEIGHT
LEFT = LEFT_EDGE * WIDTH
RIGHT = WIDTH - LEFT
PLOT_TOP = 1.45
PLOT_BOTTOM = 3.95
MAX_ROWS = 8
# Rough advance of one character at 9.5 pt, used to size a label gutter without rendering.
CHAR_WIDTH_IN = 0.078


@dataclass
class Canvas:
    fig: Figure
    ax: Axes
    theme: ChartTheme
    family: str

    def text(self, x: float, y: float, s: str, size: float = 9.5, colour: str | None = None, weight: str = "normal",
             ha: str = "left", va: str = "center") -> None:
        self.ax.text(x, y, s, fontsize=size, color=colour or self.theme.ink, fontweight=weight, ha=ha, va=va,
                     family=self.family, zorder=6)

    def bar(self, x: float, y: float, w: float, h: float, colour: str, z: float = 2) -> None:
        add_rounded_bar(self.ax, x, y, w, h, colour, self.theme.corner_radius_in, z)

    def hline(self, x0: float, x1: float, y: float, colour: str, lw: float = 1.0, z: float = 1) -> None:
        self.ax.plot([x0, x1], [y, y], color=colour, lw=lw, solid_capstyle="round", zorder=z)


def new_canvas(theme: ChartTheme) -> Canvas:
    fig = new_figure(theme)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(HEIGHT, 0)
    ax.axis("off")
    return Canvas(fig, ax, theme, chart_font_family())


def frame(canvas: Canvas, title: str, subtitle: str, footer: str) -> None:
    draw_title(canvas.fig, title, subtitle, canvas.theme, canvas.family)
    draw_footer(canvas.fig, footer, canvas.theme, canvas.family)


def finish(canvas: Canvas) -> bytes:
    return render_png(canvas.fig, canvas.theme)


def on_colour(fill: str, theme: ChartTheme) -> str:
    """Label colour that stays readable on ``fill``: dark ink on light fills, light ink on dimmed ones."""
    r, g, b = (int(fill[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return theme.bg if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45 else theme.ink


def require_values(values: list[float]) -> None:
    """Rejects empty input and any non-numeric or non-finite value before any drawing."""
    if not values:
        raise ChartError("chart input must not be empty")
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ChartError(f"value {v!r} is not a finite number")
