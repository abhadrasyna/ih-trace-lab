import pytest

from src.lib.charts.columns import Column, render_columns
from src.lib.charts.composition import Part, render_composition
from src.lib.charts.errors import ChartError
from src.lib.charts.rate_bars import RateRow, render_rate_bars
from src.lib.charts.trend import TrendReference, TrendSeries, render_trend

PNG = b"\x89PNG"


def test_rate_bars_render_and_reject_out_of_range():
    rows = [RateRow("First seen 0-7 days", 65.0, "65%"), RateRow("31-90 days", 34.0, "34%", "dim_red")]
    assert render_rate_bars(rows, title="t", subtitle="s", footer="f").startswith(PNG)
    assert render_rate_bars(rows, title="t", inline_labels=True, track=False).startswith(PNG)
    with pytest.raises(ChartError):
        render_rate_bars([RateRow("x", 120.0, "120%")], title="t")
    with pytest.raises(ChartError):
        render_rate_bars([], title="t")


def test_columns_render_and_reject_negative():
    cols = [Column("1 Nov", 12.3, "12%", "dim_red"), Column("4 Nov", 15.6, "16%", tag="upgrade")]
    assert render_columns(cols, title="t").startswith(PNG)
    with pytest.raises(ChartError):
        render_columns([Column("a", -1.0, "-1")], title="t")


def test_trend_render_and_reject_bad_input():
    s = TrendSeries("a", [60.0, 67.0, 63.0], "red", end_text="6001", label_points=(1,))
    ref = TrendReference(60.0, "baseline")
    png = render_trend(["1", "2", "3"], [s], title="t", lo=50, hi=75, ticks=[50, 60, 70],
                       value_fmt=lambda v: f"{v:.0f}%", reference=ref)
    assert png.startswith(PNG)
    with pytest.raises(ChartError):
        render_trend(["1"], [s], title="t", lo=50, hi=75, ticks=[], value_fmt=str)
    with pytest.raises(ChartError):
        render_trend(["1", "2", "3"], [TrendSeries("a", [60.0, 99.0, 63.0])], title="t", lo=50, hi=75,
                     ticks=[], value_fmt=str)


def test_composition_render_and_reject_zero_total():
    parts = [Part("0-7 days", 6069, "6,069 households"), Part("8-30 days", 9368), Part("31-90 days", 731, "", "violet")]
    assert render_composition(parts, title="t").startswith(PNG)
    with pytest.raises(ChartError):
        render_composition([Part("a", 0.0)], title="t")


def test_spread_labels_separates_close_end_labels_and_keeps_far_ones():
    from src.lib.charts.trend import spread_labels

    out = spread_labels({0: 2.0, 1: 2.01, 2: 3.5}, gap=0.2)
    assert out[1] - out[0] >= 0.2 and out[2] == 3.5 and out[0] == 2.0
