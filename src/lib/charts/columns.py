"""Columns: one value per period or category, labelled on top, for a few time buckets or ranked groups."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from src.lib.charts.canvas import LEFT, PLOT_TOP, RIGHT, finish, frame, new_canvas, require_values
from src.lib.charts.errors import ChartError
from src.lib.charts.theme import DARK, ChartTheme, resolve_colour

logger = logging.getLogger(__name__)

MAX_COLUMNS = 8
BASELINE_Y = 3.5
COLUMN_WIDTH_IN = 0.7
HEADROOM = 1.12


@dataclass(frozen=True)
class Column:
    label: str
    value: float
    text: str
    colour: str = "red"
    tag: str = ""  # one short word under the label, in the bar colour (e.g. "upgrade")


def render_columns(
    columns: Sequence[Column], *, title: str, subtitle: str = "", footer: str = "", vmax: float | None = None,
    theme: ChartTheme = DARK,
) -> bytes:
    """Renders the columns to PNG bytes; the tallest fills the plot unless ``vmax`` fixes the scale."""
    if not 1 <= len(columns) <= MAX_COLUMNS:
        raise ChartError(f"columns need 1 to {MAX_COLUMNS} items, got {len(columns)}")
    values = [col.value for col in columns]
    require_values(values)
    if any(v < 0 for v in values):
        raise ChartError("column values must not be negative")
    scale = vmax or max(values) * HEADROOM or 1.0
    try:
        c = new_canvas(theme)
        frame(c, title, subtitle, footer)
        gap = (RIGHT - LEFT) / len(columns)
        for i, col in enumerate(columns):
            cx = LEFT + gap * (i + 0.5)
            h = col.value / scale * (BASELINE_Y - PLOT_TOP)
            colour = resolve_colour(col.colour, theme)
            c.bar(cx - COLUMN_WIDTH_IN / 2, BASELINE_Y - h, COLUMN_WIDTH_IN, h, colour)
            c.text(cx, BASELINE_Y - h - 0.17, col.text, size=11.5, weight="bold", ha="center")
            c.text(cx, BASELINE_Y + 0.2, col.label, colour=theme.muted, ha="center")
            if col.tag:
                c.text(cx, BASELINE_Y + 0.42, col.tag, size=8.5, colour=colour, weight="bold", ha="center")
        png = finish(c)
    except ChartError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"columns render failed: {exc}") from exc
    logger.info("columns rendered %d bytes", len(png))
    return png
