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


def test_unique_households_per_code():
    rows = [_row("a", "6001", "true"), _row("b", "6001", "true"), _row("c", "6001", "true")]
    rows[2]["householdId"] = "h2"
    stats = mod.breakdown(rows)
    assert stats["code_households"]["6001"] == 2
    assert stats["unique_households"] == 2


def test_print_spread_with_and_without_rate(capsys):
    stats = mod.breakdown([_row("a", "6001", "true"), _row("b", "1003", "false")])
    mod.print_spread(stats, {"total": 10}, 5)
    out = capsys.readouterr().out
    assert "50.0%" in out and "10.0%" in out
    mod.print_spread(stats, None, 5)
    assert "n/a" in capsys.readouterr().out


def test_spread_counts_unique_sessions(capsys):
    stats = mod.breakdown([_row("a", "6001", "true"), _row("a", "6001", "true"), _row("b", "1003", "false"),
                           _row("c", "1003", "false"), _row("d", "1003", "false")])
    mod.print_spread(stats, {"total": 10}, 5)
    lines = {ln.split()[0]: ln for ln in capsys.readouterr().out.splitlines() if ln.split()[:1] in (["6001"], ["1003"])}
    assert stats["code_sessions"]["6001"] == 1
    assert "75.0%" in lines["1003"] and "30.0%" in lines["1003"]
    assert "25.0%" in lines["6001"] and "10.0%" in lines["6001"]
    assert list(lines) == ["1003", "6001"]


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
