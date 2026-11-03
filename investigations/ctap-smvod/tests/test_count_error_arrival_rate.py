"""Tests for count_error_arrival_rate.py."""
from __future__ import annotations

from datetime import date

import pytest

from conftest import load_script

mod = load_script("count_error_arrival_rate.py")
D = date


def test_read_daily_file_blank_short_and_duplicate(tmp_path):
    p = tmp_path / "2026-10_shaka-error-session.csv"
    p.write_text("session_date,1003,6007\n2026-10-01,5,3\n2026-10-02,1,\n")
    assert mod.read_daily_file(p) == {"1003": {D(2026, 10, 1): 5, D(2026, 10, 2): 1},
                                      "6007": {D(2026, 10, 1): 3, D(2026, 10, 2): 0}}
    p.write_text("session_date,1003,6007\n2026-10-01,5\n")
    with pytest.raises(ValueError):
        mod.read_daily_file(p)
    p.write_text("session_date,6007\n2026-10-01,1\n2026-10-01,2\n")
    with pytest.raises(ValueError):
        mod.read_daily_file(p)


def test_load_tenant_zero_fills_code_missing_from_a_file_and_rejects_overlap(tmp_path):
    daily = tmp_path / "ZA" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-10_shaka-error-session.csv").write_text("session_date,6007,6008\n2026-10-31,1,4\n")
    (daily / "2026-11_shaka-error-session.csv").write_text("session_date,6007\n2026-11-01,2\n")
    got = mod.load_tenant(tmp_path / "ZA", "shaka-error-session")
    assert got["6008"] == {D(2026, 10, 31): 4, D(2026, 11, 1): 0}
    assert got["6007"] == {D(2026, 10, 31): 1, D(2026, 11, 1): 2}
    (daily / "2026-11b_shaka-error-session.csv").write_text("session_date,6007\n2026-11-01,9\n")
    with pytest.raises(ValueError):
        mod.load_tenant(tmp_path / "ZA", "shaka-error-session")


def test_select_codes_families_all_list_and_unknown():
    avail = {"1003", "6007", "4032", "E31012", "3016"}
    assert mod.select_codes(avail, "families") == ["1003", "3016", "6007"]
    assert mod.select_codes(avail, "all") == ["1003", "3016", "4032", "6007", "E31012"]
    assert mod.select_codes(avail, "6007, 1003") == ["1003", "6007"]
    with pytest.raises(ValueError):
        mod.select_codes(avail, "9999")
    assert mod.select_codes(avail, "6xxx,1003,6007") == ["1003", "6007"]
    assert mod.select_codes(avail | {"6001"}, "6XXX") == ["6001", "6007"]
    assert mod.select_codes(avail, "other") == ["E31012"]
    with pytest.raises(ValueError):
        mod.select_codes(avail, "9xxx")


def test_family_of():
    assert [mod.family_of(c) for c in ("6007", "1003", "E31012", "ERROR_X")] == ["6xxx", "1xxx", "other", "other"]


def test_combine_and_stats_drop_partial_ends():
    a, b = {D(2026, 10, 1): 100, D(2026, 10, 2): 2}, {D(2026, 10, 1): 5}
    assert mod.combine({"A": a, "B": b}) == {D(2026, 10, 1): 105, D(2026, 10, 2): 2}
    daily = {D(2026, 10, d): n for d, n in [(1, 100), (2, 2), (3, 4), (4, 100)]}
    assert mod.stats(daily, True, True)["mean"] == 3
    assert mod.stats(daily, False, True)["max"] == 100
    with pytest.raises(ValueError):
        mod.stats({D(2026, 10, 1): 1}, drop_first=True, drop_last=False)


def test_check_aligned_rejects_gaps_short_and_mismatched_tenants():
    full = {D(2026, 10, 1): 1, D(2026, 10, 2): 1, D(2026, 10, 3): 1}
    mod.check_aligned({"A": full, "B": dict(full)}, None, None)
    with pytest.raises(ValueError):
        mod.check_aligned({"A": {D(2026, 10, 1): 1, D(2026, 10, 3): 1}}, None, None)
    with pytest.raises(ValueError):
        mod.check_aligned({"A": full, "B": {D(2026, 10, 1): 1, D(2026, 10, 2): 1}}, None, None)
    with pytest.raises(ValueError):
        mod.check_aligned({"A": full}, None, D(2026, 10, 9))


def test_summary_family_sum_and_matrix_rows():
    days = {D(2026, 10, 1): 1, D(2026, 10, 2): 3}
    per_metric = {"sessions": {"A": {"6007": days, "6008": {D(2026, 10, 1): 2, D(2026, 10, 2): 2}}},
                  "households": {"A": {"6007": days, "6008": days}}}
    combined = mod.combined_by_code(per_metric, ["6007", "6008"])
    text = mod.summary_table(combined, ["6007", "6008"], drop_first=False, drop_last=False)
    assert "6xxx (sum of codes) | 4.0/3/5 |" in text
    assert mod.matrix_rows(combined, ["6008"]) == [[D(2026, 10, 1), "6008", 2, 1], [D(2026, 10, 2), "6008", 2, 3]]


def test_top_series_collapses_rest_into_other_and_rejects_bad_input():
    from lib.arrival_rate_chart import top_series
    per_code = {"1001": {D(2026, 10, 1): 9, D(2026, 10, 2): 9}, "6007": {D(2026, 10, 1): 2, D(2026, 10, 2): 1},
                "6008": {D(2026, 10, 1): 1}}
    got = top_series(per_code, 1)
    assert list(got) == ["1001", "other (2 codes)"]
    assert got["other (2 codes)"] == {D(2026, 10, 1): 3, D(2026, 10, 2): 1}
    with pytest.raises(ValueError):
        top_series(per_code, 0)
    with pytest.raises(ValueError):
        top_series(per_code, 9)
    with pytest.raises(ValueError):
        top_series({}, 3)


def test_render_arrival_chart_returns_png_and_fails_on_single_day():
    from lib.arrival_rate_chart import render_arrival_chart
    from src.lib.charts.errors import ChartError
    two = {"6007": {D(2026, 10, 1): 2, D(2026, 10, 2): 5}}
    assert render_arrival_chart(two, "sessions", "t").startswith(b"\x89PNG")
    with pytest.raises(ChartError):
        render_arrival_chart({"6007": {D(2026, 10, 1): 2}}, "sessions", "t")
