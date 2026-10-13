"""Tests for count_error_by_content.py."""
from __future__ import annotations

from datetime import date

import pytest

from conftest import load_script

mod = load_script("count_error_by_content.py")


def test_collect_hits_filters_6xxx():
    rows = [{"content": "A", "error_codes": "6001", "sessionId": "s1", "householdId": "h1"},
            {"content": "B", "error_codes": "1003", "sessionId": "s2", "householdId": "h2"},
            {"content": "", "error_codes": "6007", "sessionId": "s3", "householdId": "h3"}]
    assert mod.collect_hits(rows, "6") == [("6001", "A", "s1", "h1"), ("6007", "(blank)", "s3", "h3")]


def test_collect_hits_blank_ids_raise():
    with pytest.raises(ValueError):
        mod.collect_hits([{"content": "A", "error_codes": "6001", "sessionId": "s1", "householdId": ""}], "6")


def test_aggregate_unique_households_and_rollup():
    hits = [("6001", "A", "s1", "h1"), ("6001", "A", "s2", "h1"), ("6002", "A", "s2", "h1"), ("6001", "A", "s3", "h2")]
    assert mod.aggregate(hits, by_code=True) == {("6001", "A"): (3, 2), ("6002", "A"): (1, 1)}
    assert mod.aggregate(hits, by_code=False) == {("ALL", "A"): (3, 2)}


def test_date_range_inclusive_and_invalid():
    assert len(mod.date_range(date(2026, 10, 1), date(2026, 10, 10))) == 10
    with pytest.raises(ValueError):
        mod.date_range(date(2026, 10, 10), date(2026, 10, 1))


def test_read_rows_missing_column_raises(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("sessionId,content\na,b\n")
    with pytest.raises(ValueError):
        mod.read_rows(p)
