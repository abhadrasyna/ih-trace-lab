"""Scratch-only helper — not for src/ or scripts/dev/ import. Graduate (with tests) before reuse there."""
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.dates as mdates  # noqa: E402

from src.lib.charts.axes import format_value_axis, padded_range, style_axes  # noqa: E402
from src.lib.charts.errors import ChartError, require_series  # noqa: E402
from src.lib.charts.fig import MARGIN_BOTTOM, TWO_ROW_HEIGHT, new_figure, render_png  # noqa: E402
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family  # noqa: E402
from src.lib.charts.title import TITLE_X, draw_title  # noqa: E402

KPI_LABEL_Y = 0.915
KPI_VALUE_Y = 0.89
AXES_TOP_WITH_KPI = 0.80
AXES_BOTTOM_WITH_FOOTER = 0.14
FOOTER_Y = 0.02
FOOTER_FONT_SIZE = 8.5
KPI_LABEL_FONT_SIZE = 8.5
KPI_VALUE_FONT_SIZE = 20


def render_line(
    xs: Sequence[float | datetime],
    ys: Sequence[float],
    *,
    title: str,
    kpi: tuple[str, str] | None = None,
    footer: str = "",
    fill: bool = True,
    theme: ChartTheme = DARK,
) -> bytes:
    """Single neutral (unsigned) series as PNG bytes: ``series[0]`` line, optional light area fill.

    For counts, which carry no good/bad sign. ``xs`` may be datetimes (axis shows HH:MM). Zero baseline.
    ``kpi`` is (label, value) drawn under the title; ``footer`` is small muted metadata at the bottom.
    """
    require_series(xs, ys)
    try:
        family = chart_font_family()
        fig = new_figure(theme, TWO_ROW_HEIGHT if kpi else 4.9)
        fig.subplots_adjust(
            top=AXES_TOP_WITH_KPI if kpi else 0.88,
            bottom=AXES_BOTTOM_WITH_FOOTER if footer else MARGIN_BOTTOM,
        )
        ax = fig.add_subplot(111)
        colour = theme.series[0]
        ax.plot(xs, ys, color=colour, lw=1.8, solid_capstyle="round")
        if fill:
            ax.fill_between(xs, 0, ys, color=colour, alpha=theme.fill_alpha_green, lw=0)
        ax.axhline(0, color=theme.muted, lw=0.8)
        ax.set_ylim(0, padded_range([*ys, 0.0])[1])
        style_axes(ax, theme, family)
        format_value_axis(ax)
        if isinstance(xs[0], datetime):
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            for label in ax.get_xticklabels():
                label.set_family(family)
        draw_title(fig, title, "", theme, family)
        if kpi:
            fig.text(TITLE_X, KPI_LABEL_Y, kpi[0], color=theme.muted, fontsize=KPI_LABEL_FONT_SIZE, family=family, va="top")
            fig.text(TITLE_X, KPI_VALUE_Y, kpi[1], color=theme.ink, fontsize=KPI_VALUE_FONT_SIZE, family=family,
                     fontweight="bold", va="top")
        if footer:
            fig.text(TITLE_X, FOOTER_Y, footer, color=theme.muted, fontsize=FOOTER_FONT_SIZE, family=family, alpha=0.8)
        return render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"line render failed: {exc}") from exc
