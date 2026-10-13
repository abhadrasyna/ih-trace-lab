"""Tests for count_error_by_content.py."""
from __future__ import annotations

from datetime import date

import pytest

from conftest import load_script

mod = load_script("count_error_by_content.py")


def test_count_by_content_filters_6xxx():
    rows = [{"content": "A", "error_codes": "6001"}, {"content": "A", "error_codes": "6001"},
            {"content": "B", "error_codes": "1003"}, {"content": "", "error_codes": "6007"}]
    counts = mod.count_by_content(rows, "6")
    assert counts == {("6001", "A"): 2, ("6007", "(blank)"): 1}


def test_date_range_inclusive_and_invalid():
    assert len(mod.date_range(date(2026, 10, 1), date(2026, 10, 10))) == 10
    with pytest.raises(ValueError):
        mod.date_range(date(2026, 10, 10), date(2026, 10, 1))


def test_read_rows_missing_column_raises(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("sessionId,content\na,b\n")
    with pytest.raises(ValueError):
        mod.read_rows(p)
