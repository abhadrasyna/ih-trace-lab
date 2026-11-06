"""Offline tests for chart_session_error_impact (synthetic table rows, tmp_path only)."""
from __future__ import annotations

from datetime import date

import pytest

from scripts import chart_session_error_impact as csei
from src.lib.charts.errors import ChartError

ROWS = [
    {"day": "2026-11-02", "unique_sessions": "200", "error_sessions": "12", "sessions_6001": "8", "other_error_sessions": "4",
     "error_sessions_in_session_file": "10", "sessions_6001_in_session_file": "7"},
    {"day": "2026-11-01", "unique_sessions": "100", "error_sessions": "5", "sessions_6001": "3", "other_error_sessions": "2",
     "error_sessions_in_session_file": "5", "sessions_6001_in_session_file": "3"},
    {"day": "all", "unique_sessions": "300", "error_sessions": "17", "sessions_6001": "11", "other_error_sessions": "6",
     "error_sessions_in_session_file": "15", "sessions_6001_in_session_file": "10"},
]


def test_values_are_sorted_skip_all_row_and_stacks_sum_to_unique():
    labels, values, colours = csei.counts_values(ROWS)
    assert labels[:2] == ["11-01 all", "11-01 6001"] and values == [100.0, 3.0, 200.0, 8.0]
    assert colours[:2] == [csei.DARK.ink, csei.DARK.red] and len(colours) == 4
    _, series = csei.pct_stacked_values(ROWS)
    assert [sum(col) for col in zip(*series.values())] == [100.0, 200.0]
    assert series["other error"] == [2.0, 3.0] and series["no error"] == [95.0, 190.0]
    _, share = csei.share_values(ROWS)
    assert share == {"6001-impacted": [3.0, 8.0], "other error": [2.0, 4.0]}


def test_inconsistent_table_is_rejected():
    bad = [{**ROWS[1], "error_sessions_in_session_file": "500"}]
    with pytest.raises(csei.ChartInputError):
        csei.pct_stacked_values(bad)


def test_charts_written_and_failures_skipped(tmp_path):
    charts = csei.build_charts(ROWS, tenant="ZA", start=date(2026, 11, 1), end=date(2026, 11, 2))
    assert len(charts) == 3
    ok = csei.write_charts(charts, tmp_path, "ZA", lambda a: f"{a}.png")
    assert len(ok) == 3 and ok[0].read_bytes().startswith(b"\x89PNG")

    def boom() -> bytes:
        raise ChartError("bad")

    assert csei.write_charts({"x": boom, **charts}, tmp_path, "ZA", lambda a: f"{a}.png") == ok


def test_read_table_missing_file_and_columns(tmp_path):
    with pytest.raises(csei.ChartInputError):
        csei.read_table(tmp_path / "nope.csv")
    path = tmp_path / "t.csv"
    path.write_text("day,unique_sessions\n2026-11-01,1\n")
    with pytest.raises(csei.ChartInputError, match="missing columns"):
        csei.read_table(path)
