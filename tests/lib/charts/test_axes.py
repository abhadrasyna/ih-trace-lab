import pytest

from src.lib.charts.axes import format_count, format_pct, format_value_axis, nice_ticks, padded_range, style_axes
from src.lib.charts.fig import new_figure
from src.lib.charts.theme import DARK


def test_format_count_abbreviates():
    assert format_count(1500) == "1.5k"
    assert format_count(2_000_000) == "2M"
    assert format_count(-1500) == "-1.5k"
    assert format_count(0) == "0"
    assert format_count(999) == "999"


def test_format_pct():
    assert format_pct(12.5) == "12.5%"
    assert format_pct(3) == "3%"


def test_padded_range_flat_and_empty():
    assert padded_range([5, 5]) == (4.0, 6.0)
    with pytest.raises(ValueError):
        padded_range([])


def test_nice_ticks():
    assert nice_ticks(0, 100) == [0, 50, 100]
    ticks = nice_ticks(0, 97)
    assert ticks[0] <= 0 and ticks[-1] >= 97
    assert nice_ticks(3, 3) == [3]
    with pytest.raises(ValueError):
        nice_ticks(0, 1, target=1)


def test_style_axes_quiet_chrome():
    ax = new_figure(DARK).add_subplot(111)
    style_axes(ax, DARK, "DejaVu Sans")
    assert not ax.spines["top"].get_visible() and not ax.spines["right"].get_visible()
    assert ax.get_axisbelow() is True


def test_format_rounding_edges():
    assert format_count(999_950) == "1M"
    assert format_count(999_960_000) == "1B"
    assert format_count(-0.04) == "0"
    assert format_pct(-0.04) == "0%"
    assert format_pct(-2.5) == "-2.5%"


@pytest.mark.parametrize("horizontal", [False, True])
def test_format_value_axis_vertical_and_horizontal(horizontal):
    ax = new_figure(DARK).add_subplot(111)
    format_value_axis(ax, horizontal)
    value_axis, other_axis = (ax.xaxis, ax.yaxis) if horizontal else (ax.yaxis, ax.xaxis)
    assert value_axis.get_major_formatter()(2000) == "2k"
    assert other_axis.get_major_formatter()(2000) != "2k"


def test_format_value_axis_keeps_fractions():
    ax = new_figure(DARK).add_subplot(111)
    format_value_axis(ax)
    assert ax.yaxis.get_major_formatter()(0.25) == "0.25"


def test_value_axis_labels_never_misreport_the_tick():
    ax = new_figure(DARK).add_subplot(111)
    format_value_axis(ax)
    fmt = ax.yaxis.get_major_formatter()
    assert [fmt(v) for v in (1250, 3750, 10050, 2_500_000)] == ["1.25k", "3.75k", "10.05k", "2.5M"]
    assert [fmt(v) for v in (1000, 10_000, 20_000, 100_000, 1_000_000)] == ["1k", "10k", "20k", "100k", "1M"]
    assert fmt(1234.5) == "1234.5"
    assert fmt(1234567) == "1234567"
    assert fmt(5.55e-17) == "0" and fmt(-5.55e-17) == "0"
