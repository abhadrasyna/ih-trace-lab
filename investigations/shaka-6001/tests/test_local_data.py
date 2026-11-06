"""Offline tests for the local-data loader."""
from __future__ import annotations

from datetime import date

import pytest

from scripts.lib.local_data import LocalDataError, date_range, load_daily

ART = "session"


def _write(directory, day, body="a,b\n1,2\n"):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{day}_{ART}.csv").write_text(body, encoding="utf-8")


def test_loader_reports_missing_dates(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    _write(first, "2026-11-01")
    _write(second, "2026-11-01", "a,b\n9,9\n")  # lower-priority duplicate, ignored
    _write(second, "2026-11-03")
    result = load_daily([first, second], ART, date_range(date(2026, 11, 1), date(2026, 11, 3)))
    assert result.missing == [date(2026, 11, 2)]
    assert sorted(result.found) == [date(2026, 11, 1), date(2026, 11, 3)]
    assert [row["a"] for row in result.rows] == ["1", "1"]


def test_zero_byte_file_counts_as_missing(tmp_path):
    _write(tmp_path, "2026-11-01", "")
    assert load_daily([tmp_path], ART, [date(2026, 11, 1)]).missing == [date(2026, 11, 1)]


def test_reversed_range_raises():
    with pytest.raises(LocalDataError):
        date_range(date(2026, 11, 3), date(2026, 11, 1))
