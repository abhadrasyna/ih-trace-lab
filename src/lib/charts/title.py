"""Shared title block: one place for the guide's title/subtitle type scale."""

from __future__ import annotations

from matplotlib.figure import Figure

from src.lib.charts.fig import MARGIN_RIGHT
from src.lib.charts.theme import ChartTheme

TITLE_FONT_SIZE = 16
SUBTITLE_FONT_SIZE = 10
TITLE_X = 0.13
TITLE_Y = 0.95
SUBTITLE_Y = 0.915
ELLIPSIS = "…"


def _truncate_to_fit(fig: Figure, text, title: str) -> None:
    """Shortens the drawn title with an ellipsis until its rendered width ends inside the right margin."""
    renderer = fig.canvas.get_renderer()
    limit = MARGIN_RIGHT * fig.bbox.width
    while len(title) > 1 and text.get_window_extent(renderer).x1 > limit:
        title = title.removesuffix(ELLIPSIS)[:-1].rstrip() + ELLIPSIS
        text.set_text(title)


def draw_title(fig: Figure, title: str, subtitle: str, theme: ChartTheme, family: str) -> None:
    """Draws the 16 pt bold title (truncated with an ellipsis if wider than the figure) and the 10 pt muted subtitle."""
    text = fig.text(TITLE_X, TITLE_Y, title, color=theme.ink, fontsize=TITLE_FONT_SIZE, fontweight="bold",
                    family=family)
    _truncate_to_fit(fig, text, title)
    if subtitle:
        fig.text(TITLE_X, SUBTITLE_Y, subtitle, color=theme.muted, fontsize=SUBTITLE_FONT_SIZE, family=family)
