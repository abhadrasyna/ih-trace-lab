import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from src.lib.charts.shapes import add_bars, rounded_corners_px

PNG = b"\x89PNG"


def test_rounded_corners_clamp_to_pill():
    pts = rounded_corners_px(0, 0, 100, 10, radius=50)
    assert pts[:, 1].min() == pytest.approx(0) and pts[:, 1].max() == pytest.approx(10)
    assert pts[:, 0].min() == pytest.approx(0) and pts[:, 0].max() == pytest.approx(100)


def test_zero_radius_gives_plain_rectangle():
    assert len(rounded_corners_px(0, 0, 10, 10, radius=0)) == 4


def test_add_bars_skips_zero_and_renders():
    fig = Figure(figsize=(3, 2), dpi=50)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    add_bars(ax, [0, 1, 2], [3, 0, 5], "#5ec8b4", 0.09, label="x")
    ax.set_xlim(-1, 3)
    ax.set_ylim(0, 6)
    assert len(ax.patches) == 2
    assert [p.get_height() for p in ax.patches] == [3, 5]
    fig.canvas.draw()
    vertices = np.asarray(ax.patches[0].get_path().vertices)
    assert len(vertices) > 4
