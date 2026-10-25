import re

import pytest

from src.lib.charts import stacked_bar
from src.lib.charts.errors import ChartError
from src.lib.charts.stacked_bar import render_stacked_bar, segment_label, series_colours
from src.lib.charts.theme import DARK

SERIES = {"success": [90, 40], "failed": [10, 2]}


@pytest.mark.parametrize("horizontal", [False, True])
def test_renders_png_bytes_for_vertical_and_horizontal(horizontal):
    png = render_stacked_bar(["widevine", "fairplay"], SERIES, title="t", subtitle="s", horizontal=horizontal, total=142)
    assert png.startswith(b"\x89PNG")


def test_tiny_segment_still_renders_with_legend():
    assert render_stacked_bar(["a"], {"big": [1000], "tiny": [1]}, title="t").startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "labels,series",
    [
        ([], SERIES),
        (["a", "b"], {}),
        (["a", "b"], {"x": [1]}),
        (["a", "b"], {"x": [1, -1]}),
        (["a", "b"], {"x": [1, float("nan")]}),
        (["a", "b"], {"x": [1, float("inf")]}),
        (["a", "b"], {"x": [1, None]}),
        (["a", "b"], {"x": [1, "2"]}),
    ],
)
def test_unequal_series_lengths_and_negative_values_raise_chart_error(labels, series):
    with pytest.raises(ChartError):
        render_stacked_bar(labels, series, title="t")


def test_series_colours_come_from_theme_palette():
    assert series_colours(["a", "b", "c"], None, DARK) == list(DARK.series[:3])
    mapped = series_colours(["ok", "bad", "x"], {"ok": "green", "bad": "red"}, DARK)
    assert mapped == [DARK.green, DARK.red, DARK.series[2]]
    assert DARK.green not in DARK.series and DARK.red not in DARK.series
    with pytest.raises(ChartError):
        series_colours(["a"], {"a": "#ffffff"}, DARK)


def test_segment_label_adds_share_only_with_total():
    assert segment_label(1500, None) == "1.5k"
    assert segment_label(25, 100) == "25 (25%)"


@pytest.mark.parametrize("horizontal", [False, True])
def test_stacked_bar_axis_labels_abbreviated(monkeypatch, horizontal):
    figs = []
    real = stacked_bar.render_png
    monkeypatch.setattr(stacked_bar, "render_png", lambda fig, theme: figs.append(fig) or real(fig, theme))
    render_stacked_bar(["a", "b"], {"x": [1500, 2000], "y": [500, 1000]}, title="t", horizontal=horizontal)
    ax = figs[0].axes[0]
    labels = [t.get_text() for t in (ax.get_xticklabels() if horizontal else ax.get_yticklabels())]
    assert "2k" in labels and not any(re.fullmatch(r"\d{4,}", t) for t in labels)
