"""Tests for analyze_error_report_breakdown.py."""
from __future__ import annotations

import pytest

from conftest import load_script

mod = load_script("analyze_error_report_breakdown.py")


def _row(sid: str, codes: str, wv: str, moved: str = "true") -> dict[str, str]:
    return {"sessionId": sid, "error_codes": codes, "is_wv": wv, "position_not_moved": moved,
            "start_time": "2026-10-09 05:10:00.000 UTC", "deviceId": "d1", "householdId": "h1",
            "state_sequence": "CREATE->ERROR"}


def test_breakdown_counts_codes_and_wv():
    stats = mod.breakdown([_row("a", "6001", "true"), _row("b", "6001,3016", "false"), _row("c", "6001", "true")])
    assert stats["total"] == 3
    assert stats["wv"] == 2
    assert stats["codes"]["6001"] == 3
    assert stats["codes_wv"]["6001"] == 2
    assert stats["codes_non_wv"]["3016"] == 1
    assert stats["hours"]["05"] == 3


def test_breakdown_missing_column_raises():
    with pytest.raises(ValueError):
        mod.breakdown([{"sessionId": "a", "error_codes": "6001"}])


def test_error_rate():
    outcome = [{"sessionId": "a", "raw_user_agent": "Linux; Android 13; X Build/1; wv"}, {"sessionId": "b", "raw_user_agent": "Linux"}]
    rate = mod.error_rate(outcome, {"a"})
    assert rate == {"total": 2, "errors": 1, "wv_total": 1, "wv_errors": 1}


def test_pct_zero_total():
    assert mod.pct(1, 0) == "n/a"


def test_error_rate_missing_column_raises():
    with pytest.raises(ValueError):
        mod.error_rate([{"session_id": "a"}], {"a"})
