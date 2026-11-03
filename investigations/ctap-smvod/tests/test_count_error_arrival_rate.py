"""Tests for count_error_arrival_rate.py."""
from __future__ import annotations

from datetime import date

import pytest

from conftest import load_script

mod = load_script("count_error_arrival_rate.py")


def test_read_code_column_and_missing_code(tmp_path):
    p = tmp_path / "2026-10_shaka-error-session.csv"
    p.write_text("session_date,1003,6007\n2026-10-01,5,3\n2026-10-02,1,\n")
    assert mod.read_code_column(p, "6007") == {date(2026, 10, 1): 3, date(2026, 10, 2): 0}
    with pytest.raises(ValueError):
        mod.read_code_column(p, "9999")
    p.write_text("session_date,1003,6007\n2026-10-01,5\n")
    with pytest.raises(ValueError):
        mod.read_code_column(p, "6007")


def test_combine_sums_across_tenants():
    a, b = {date(2026, 10, 1): 2, date(2026, 10, 2): 1}, {date(2026, 10, 1): 5}
    assert mod.combine({"A": a, "B": b}) == {date(2026, 10, 1): 7, date(2026, 10, 2): 1}


def test_stats_drops_partial_ends():
    daily = {date(2026, 10, d): n for d, n in [(1, 100), (2, 2), (3, 4), (4, 100)]}
    assert mod.stats(daily, drop_first=True, drop_last=True)["mean"] == 3
    assert mod.stats(daily, drop_first=False, drop_last=True)["max"] == 100
    with pytest.raises(ValueError):
        mod.stats({date(2026, 10, 1): 1}, drop_first=True, drop_last=False)


def test_check_aligned_rejects_gaps_short_and_mismatched_tenants():
    d = date
    full = {d(2026, 10, 1): 1, d(2026, 10, 2): 1, d(2026, 10, 3): 1}
    mod.check_aligned({"A": full, "B": dict(full)}, None, None)
    with pytest.raises(ValueError):
        mod.check_aligned({"A": {d(2026, 10, 1): 1, d(2026, 10, 3): 1}}, None, None)
    with pytest.raises(ValueError):
        mod.check_aligned({"A": full, "B": {d(2026, 10, 1): 1, d(2026, 10, 2): 1}}, None, None)
    with pytest.raises(ValueError):
        mod.check_aligned({"A": full}, None, d(2026, 10, 9))


def test_load_tenant_rejects_overlapping_files(tmp_path):
    daily = tmp_path / "ZA" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-10_shaka-error-session.csv").write_text("session_date,6007\n2026-10-01,1\n")
    assert mod.load_tenant(tmp_path / "ZA", "shaka-error-session", "6007") == {date(2026, 10, 1): 1}
    (daily / "2026-10b_shaka-error-session.csv").write_text("session_date,6007\n2026-10-01,2\n")
    with pytest.raises(ValueError):
        mod.load_tenant(tmp_path / "ZA", "shaka-error-session", "6007")
