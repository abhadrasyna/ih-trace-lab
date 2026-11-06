"""Shared title block: one place for the guide's title/subtitle/footer type scale and the single left edge."""

from __future__ import annotations

from matplotlib.figure import Figure

from src.lib.charts.fig import MARGIN_RIGHT
from src.lib.charts.theme import ChartTheme

TITLE_FONT_SIZE = 15
SUBTITLE_FONT_SIZE = 9.5
FOOTER_FONT_SIZE = 8
# One left edge for title, subtitle, header, footer and (in canvas charts) row labels and bars.
LEFT_EDGE = 0.05
TITLE_X = LEFT_EDGE
TITLE_Y = 0.95
SUBTITLE_Y = 0.915
FOOTER_Y = 0.03
ELLIPSIS = "…"


def _truncate_to_fit(fig: Figure, text, title: str) -> None:
    """Shortens the drawn title with an ellipsis until its rendered width ends inside the right margin."""
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]  # Agg canvas only; absent from the base-class stubs
    limit = MARGIN_RIGHT * fig.bbox.width
    while len(title) > 1 and text.get_window_extent(renderer).x1 > limit:
        title = title.removesuffix(ELLIPSIS)[:-1].rstrip() + ELLIPSIS
        text.set_text(title)


def draw_title(fig: Figure, title: str, subtitle: str, theme: ChartTheme, family: str) -> None:
    """Draws the bold finding title (truncated with an ellipsis if wider than the figure) and the muted measure subtitle."""
    text = fig.text(TITLE_X, TITLE_Y, title, color=theme.ink, fontsize=TITLE_FONT_SIZE, fontweight="bold",
                    family=family, va="center")
    _truncate_to_fit(fig, text, title)
    if subtitle:
        fig.text(TITLE_X, SUBTITLE_Y, subtitle, color=theme.muted, fontsize=SUBTITLE_FONT_SIZE, family=family,
                 va="center")


def draw_footer(fig: Figure, footer: str, theme: ChartTheme, family: str) -> None:
    """Draws the one-line scope footer (tenant, period, base size, caveat) on the shared left edge."""
    if footer:
        fig.text(LEFT_EDGE, FOOTER_Y, footer, color=theme.muted, fontsize=FOOTER_FONT_SIZE, family=family, va="center")
