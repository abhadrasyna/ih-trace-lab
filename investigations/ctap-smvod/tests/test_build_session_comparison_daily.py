"""Tests for build_session_comparison_daily.py (offline)."""
from __future__ import annotations

from datetime import date

import pytest

from conftest import load_script

mod = load_script("build_session_comparison_daily.py")
DAY = date(2026, 10, 14)


def test_date_range_inclusive_and_bad_order_raises():
    assert mod.date_range(DAY, date(2026, 10, 16)) == [DAY, date(2026, 10, 15), date(2026, 10, 16)]
    with pytest.raises(ValueError):
        mod.date_range(DAY, date(2026, 10, 13))


def test_build_row_full_counts():
    row = mod.build_row(DAY, "SA", {"a", "b", "c"}, {"b", "c", "d"}, {"c", "d", "e"}, 2)
    assert (row["lightstep"], row["unified"], row["debug"]) == ("3", "3", "3")
    assert (row["L_and_U"], row["L_and_D"], row["U_and_D"], row["L_and_U_and_D"]) == ("2", "1", "2", "1")
    assert (row["L_not_U"], row["U_not_L"], row["L_not_D"], row["D_not_L"]) == ("1", "1", "2", "2")
    assert row["missing_inputs"] == "" and row["lightstep_blank_rows"] == "2"


def test_build_row_missing_debug_leaves_its_columns_blank():
    row = mod.build_row(DAY, "GH", {"a"}, {"a", "b"}, None, 0)
    assert row["debug"] == "" and row["L_and_D"] == "" and row["L_and_U_and_D"] == "" and row["L_not_D"] == ""
    assert row["L_and_U"] == "1" and row["U_not_L"] == "1" and row["missing_inputs"] == "debug"


def test_upsert_replaces_same_key_and_sorts():
    old = [{"date": "2026-10-15", "tenant": "SA", "lightstep": "1"}, {"date": "2026-10-14", "tenant": "SA", "lightstep": "9"}]
    new = [{"date": "2026-10-14", "tenant": "SA", "lightstep": "5"}, {"date": "2026-10-14", "tenant": "GH", "lightstep": "2"}]
    out = mod.upsert_rows(old, new)
    assert [(r["date"], r["tenant"], r["lightstep"]) for r in out] == [
        ("2026-10-14", "GH", "2"), ("2026-10-14", "SA", "5"), ("2026-10-15", "SA", "1")]


def test_read_existing_rejects_unexpected_columns(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("date,tenant\n2026-10-14,SA\n")
    with pytest.raises(ValueError):
        mod.read_existing(p)
    assert mod.read_existing(tmp_path / "nope.csv") == []
