"""Rounded bars: a patch whose corners stay circular on screen whatever the axes' data scale."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import Patch
from matplotlib.path import Path

ARC_STEPS = 8


def rounded_corners_px(x0: float, y0: float, x1: float, y1: float, radius: float) -> np.ndarray:
    """Outline of a rounded rectangle in pixel space; ``radius`` is clamped so a thin bar becomes a pill."""
    r = max(0.0, min(radius, abs(x1 - x0) / 2, abs(y1 - y0) / 2))
    if r == 0:
        return np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    sx = 1 if x1 >= x0 else -1
    sy = 1 if y1 >= y0 else -1
    corners = (
        (x0 + sx * r, y0 + sy * r, 180),
        (x1 - sx * r, y0 + sy * r, 270),
        (x1 - sx * r, y1 - sy * r, 0),
        (x0 + sx * r, y1 - sy * r, 90),
    )
    pts: list[tuple[float, float]] = []
    for cx, cy, start in corners:
        for k in range(ARC_STEPS + 1):
            a = math.radians(start + 90 * k / ARC_STEPS)
            pts.append((cx + r * math.cos(a) * sx, cy + r * math.sin(a) * sy))
    return np.array(pts)


class RoundedBar(Patch):
    """A data-space rectangle drawn with circular corners of ``radius_in`` inches."""

    def __init__(self, x: float, y: float, w: float, h: float, radius_in: float, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._rect = (x, y, x + w, y + h)
        self._radius_in = radius_in
        # Plain rectangle until drawn, so autoscaling sees the right data limits.
        self._path = Path([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], closed=True)

    def get_path(self) -> Path:
        return self._path

    # Rectangle-compatible accessors so code written against ``ax.bar`` patches keeps working.
    def get_x(self) -> float:
        return self._rect[0]

    def get_y(self) -> float:
        return self._rect[1]

    def get_width(self) -> float:
        return self._rect[2] - self._rect[0]

    def get_height(self) -> float:
        return self._rect[3] - self._rect[1]

    def draw(self, renderer: object) -> None:
        trans = self.axes.transData
        x0, y0, x1, y1 = self._rect
        (px0, py0), (px1, py1) = trans.transform([(x0, y0), (x1, y1)])
        radius = self._radius_in * self.axes.figure.dpi
        outline = rounded_corners_px(px0, py0, px1, py1, radius)
        self._path = Path(trans.inverted().transform(outline), closed=True)
        super().draw(renderer)  # type: ignore[arg-type]


def add_bars(
    ax: Axes,
    positions: Sequence[float],
    sizes: Sequence[float],
    colours: Sequence[str] | str,
    radius_in: float,
    *,
    bases: Sequence[float] | None = None,
    horizontal: bool = False,
    thickness: float = 0.65,
    edge: str | None = None,
    label: str | None = None,
) -> None:
    """Adds one rounded bar per position (a ``bar``/``barh`` replacement); zero-size bars are skipped.

    Limits are the caller's job: patches do not autoscale a baseline the way ``ax.bar`` does. ``label`` names the
    first bar drawn so ``ax.legend`` can pick the series up.
    """
    base = bases if bases is not None else [0.0] * len(positions)
    colour_list = [colours] * len(positions) if isinstance(colours, str) else list(colours)
    for pos, size, start, colour in zip(positions, sizes, base, colour_list, strict=True):
        if size == 0:
            continue
        if horizontal:
            bar = add_rounded_bar(ax, start, pos - thickness / 2, size, thickness, colour, radius_in, edge=edge)
        else:
            bar = add_rounded_bar(ax, pos - thickness / 2, start, thickness, size, colour, radius_in, edge=edge)
        if label is not None:
            bar.set_label(label)
            label = None


def add_rounded_bar(
    ax: Axes, x: float, y: float, w: float, h: float, colour: str, radius_in: float, zorder: float = 2, edge: str | None = None
) -> RoundedBar:
    """Adds one rounded bar; ``edge`` (usually ``bg``) draws a thin separator for stacked segments."""
    patch = RoundedBar(
        x, y, w, h, radius_in, facecolor=colour, edgecolor=edge or "none", linewidth=1.0 if edge else 0, zorder=zorder
    )
    ax.add_patch(patch)
    return patch
