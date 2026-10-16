import pytest

from src.lib.charts.errors import ChartError
from src.lib.charts.signed_line import insert_zero_crossings, render_signed_line, split_by_sign


def test_signed_line_returns_png():
    png = render_signed_line([0, 1, 2, 3], [1.0, -2.0, 3.0, -1.0], title="t", subtitle="s")
    assert png.startswith(b"\x89PNG")


def test_split_by_sign_masks_opposite_side():
    pos, neg = split_by_sign([1, -1, 0])
    assert pos.mask.tolist() == [False, True, False]
    assert neg.mask.tolist() == [True, False, False]


def test_zero_crossing_inserted_where_sign_flips():
    x, y = insert_zero_crossings([0, 2], [1.0, -1.0])
    assert x.tolist() == [0.0, 1.0, 2.0]
    assert y.tolist() == [1.0, 0.0, -1.0]


def test_mismatched_lengths_raise_chart_error():
    with pytest.raises(ChartError):
        render_signed_line([1, 2], [1], title="t")


def test_empty_input_raises_chart_error():
    with pytest.raises(ChartError):
        render_signed_line([], [], title="t")


def test_non_numeric_input_is_wrapped_in_chart_error():
    with pytest.raises(ChartError):
        render_signed_line([1, 2], ["a", "b"], title="t")
