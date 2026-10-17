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


def test_month_file_maps_sa_to_za_and_keeps_other_codes(tmp_path):
    assert mod.month_file(tmp_path, "SA", DAY) == tmp_path / "ZA" / "daily" / "2026-10_session-comparison.csv"
    assert mod.month_file(tmp_path, "GH", DAY) == tmp_path / "GH" / "daily" / "2026-10_session-comparison.csv"


def test_month_store_upsert_replaces_same_day_and_keeps_others(tmp_path):
    from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter
    from src.lib.csv_io.monthly_store import MonthlyCsvStore

    store = MonthlyCsvStore(CsvFileReader(), CsvFileWriter())
    path = mod.month_file(tmp_path, "SA", DAY)
    for d, n in (("2026-10-15", {"a"}), ("2026-10-14", {"a"}), ("2026-10-14", {"a", "b"})):
        row = mod.build_row(date.fromisoformat(d), "SA", n, n, n, 0)
        store.replace_date(path, d, [row], field_order=mod.COLUMNS)
    rows = list(CsvFileReader().read_rows(str(path)))
    assert [(r["session_date"], r["lightstep"]) for r in rows] == [("2026-10-14", "2"), ("2026-10-15", "1")]
    assert list(rows[0].keys()) == mod.COLUMNS
