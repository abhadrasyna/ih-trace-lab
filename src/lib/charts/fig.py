"""Headless figure creation and the PNG-bytes save recipe (no ``pyplot``, no global state)."""

from __future__ import annotations

from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from src.lib.charts.theme import ChartTheme

BASE_WIDTH = 7.0
BASE_HEIGHT = 4.9
TWO_ROW_HEIGHT = 5.7
DPI = 170
MARGIN_LEFT = 0.13
MARGIN_RIGHT = 0.97
MARGIN_BOTTOM = 0.11
# Top margin leaves room for the title/header: more when the figure is taller (two header rows).
MARGIN_TOP_PLAIN = 0.88
MARGIN_TOP_TWO_ROW = 0.80


def new_figure(theme: ChartTheme, height: float = BASE_HEIGHT) -> Figure:
    """Returns a themed ``Figure`` bound to an Agg canvas, with explicit (never tight) margins."""
    fig = Figure(figsize=(BASE_WIDTH, height), facecolor=theme.bg)
    FigureCanvasAgg(fig)
    top = MARGIN_TOP_TWO_ROW if height >= TWO_ROW_HEIGHT else MARGIN_TOP_PLAIN
    fig.subplots_adjust(left=MARGIN_LEFT, right=MARGIN_RIGHT, bottom=MARGIN_BOTTOM, top=top)
    return fig


def render_png(fig: Figure, theme: ChartTheme) -> bytes:
    """Serialises the figure to PNG bytes; the caller owns any file I/O."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=theme.bg)
    return buf.getvalue()
