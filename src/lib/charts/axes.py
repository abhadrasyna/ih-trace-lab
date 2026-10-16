"""Axes styling, value formatters and pure range/tick maths."""

from __future__ import annotations

import math
from typing import Sequence

from matplotlib.axes import Axes

from src.lib.charts.theme import ChartTheme

_ABBREVIATIONS = ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k"))


def _trim(value: float) -> str:
    text = f"{round(value, 1):.1f}"
    return text[:-2] if text.endswith(".0") else text


def _signed(mag: float, text: str, negative: bool) -> str:
    """Prefixes '-' only when the rounded text is non-zero, so tiny negatives never show as '-0'."""
    return f"-{text}" if negative and mag and float(text.rstrip("kMB%") or 0) else text


def format_count(v: float) -> str:
    """Abbreviates a count: ``1500 -> "1.5k"``, ``2_000_000 -> "2M"``; sign is preserved."""
    mag = abs(v)
    units = ((1, ""), *reversed(_ABBREVIATIONS))
    idx = max((i for i, (t, _) in enumerate(units) if mag >= t), default=0)
    if idx < len(units) - 1 and round(mag / units[idx][0], 1) >= 1000:
        idx += 1
    threshold, suffix = units[idx]
    text = f"{_trim(mag / threshold)}{suffix}"
    return _signed(mag, text, v < 0)


def format_pct(v: float) -> str:
    """Formats a value already in percent points: ``12.5 -> "12.5%"``, ``3 -> "3%"``."""
    return _signed(abs(v), f"{_trim(abs(v))}%", v < 0)


def padded_range(values: Sequence[float], pad_frac: float = 0.08) -> tuple[float, float]:
    """Returns (lo, hi) covering the values with proportional padding; a flat series gets unit span."""
    if not values:
        raise ValueError("values must not be empty")
    lo, hi = min(values), max(values)
    span = hi - lo
    pad = span * pad_frac if span else 1.0
    return lo - pad, hi + pad


def nice_ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    """Returns evenly spaced 'nice' (1/2/5 x 10^n) tick values spanning lo..hi."""
    if target < 2:
        raise ValueError("target must be at least 2")
    if hi < lo:
        lo, hi = hi, lo
    span = hi - lo
    if span == 0:
        return [lo]
    raw = span / (target - 1)
    exp = math.floor(math.log10(raw))
    base = raw / 10**exp
    step = next(m for m in (1, 2, 5, 10) if base <= m) * 10**exp
    first = math.floor(lo / step) * step
    count = int(math.ceil((hi - first) / step - 1e-9)) + 1
    return [round(first + i * step, 10) for i in range(count)]


def style_axes(ax: Axes, theme: ChartTheme, family: str) -> None:
    """Applies the guide's quiet chrome: no top/right spines, faint grid, invisible tick marks."""
    ax.set_facecolor(theme.bg)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(theme.faint)
    ax.tick_params(length=0, colors=theme.muted, labelsize=9.5)
    ax.yaxis.grid(True, color=theme.faint, lw=0.6)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_family(family)
