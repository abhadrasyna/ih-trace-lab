"""Tests for summarize_error_eventdata.py."""
from __future__ import annotations

import pytest

from conftest import load_script

mod = load_script("summarize_error_eventdata.py")


def test_group_counts_crosstab():
    rows = [{"errorcode": "3016", "is_wv": "false"}, {"errorcode": "3016", "is_wv": "false"},
            {"errorcode": "1003", "is_wv": ""}]
    counts = mod.group_counts(rows, ["errorcode", "is_wv"])
    assert counts[("3016", "false")] == 2 and counts[("1003", "(blank)")] == 1


def test_unknown_column_raises():
    with pytest.raises(ValueError):
        mod.group_counts([{"errorcode": "1"}], ["nope"])


def test_render_percentages():
    out = mod.render(["errorcode"], mod.group_counts([{"errorcode": "a"}, {"errorcode": "b"}], ["errorcode"]), 2)
    assert "50.0%" in out
