"""Line chart coloured green above zero and red below."""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np

from src.lib.charts.axes import padded_range, style_axes
from src.lib.charts.errors import ChartError, require_series
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family

logger = logging.getLogger(__name__)


def insert_zero_crossings(xs: Sequence[float], ys: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """Adds an interpolated (x, 0) point wherever consecutive values change sign, so both colours meet at zero."""
    out_x: list[float] = [float(xs[0])]
    out_y: list[float] = [float(ys[0])]
    for x0, x1, y0, y1 in zip(xs, xs[1:], ys, ys[1:]):
        if y0 * y1 < 0:
            out_x.append(float(x0) + (x1 - x0) * (-y0 / (y1 - y0)))
            out_y.append(0.0)
        out_x.append(float(x1))
        out_y.append(float(y1))
    return np.asarray(out_x), np.asarray(out_y)


def split_by_sign(ys: Sequence[float]) -> tuple[np.ma.MaskedArray, np.ma.MaskedArray]:
    """Returns (positive, negative) masked views of ``ys``; zero points belong to both so segments join."""
    arr = np.asarray(ys, dtype=float)
    return np.ma.masked_where(arr < 0, arr), np.ma.masked_where(arr > 0, arr)


def render_signed_line(
    xs: Sequence[float], ys: Sequence[float], *, title: str, subtitle: str = "", theme: ChartTheme = DARK
) -> bytes:
    """Renders the series to PNG bytes; raises ``ChartError`` on bad input or any drawing failure."""
    require_series(xs, ys)
    try:
        family = chart_font_family()
        fig = new_figure(theme)
        ax = fig.add_subplot(111)
        x, y = insert_zero_crossings(xs, ys)
        pos, neg = split_by_sign(y)
        ax.plot(x, pos, color=theme.green, lw=1.8)
        ax.plot(x, neg, color=theme.red, lw=1.8)
        ax.fill_between(x, 0, y, where=y >= 0, interpolate=True, color=theme.green, alpha=theme.fill_alpha_green, lw=0)
        ax.fill_between(x, 0, y, where=y <= 0, interpolate=True, color=theme.red, alpha=theme.fill_alpha_red, lw=0)
        ax.axhline(0, color=theme.muted, lw=0.8)
        ax.set_ylim(*padded_range([*y.tolist(), 0.0]))
        style_axes(ax, theme, family)
        fig.text(0.13, 0.95, title, color=theme.ink, fontsize=13, fontweight="bold", family=family)
        if subtitle:
            fig.text(0.13, 0.915, subtitle, color=theme.muted, fontsize=9.5, family=family)
        png = render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"signed line render failed: {exc}") from exc
    logger.info("signed_line rendered %d bytes", len(png))
    return png
