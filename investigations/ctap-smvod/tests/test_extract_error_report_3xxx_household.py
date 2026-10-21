"""Tests for extract_error_report_3xxx_household.py."""
from __future__ import annotations

import pytest

from conftest import load_script

mod = load_script("extract_error_report_3xxx_household.py")

COLS = ["householdId", "sessionId", "error_codes", "is_wv"]


def _r(hh, sid, codes, ua=""):
    return {"householdId": hh, "sessionId": sid, "error_codes": codes, "raw_user_agent": ua}


def test_filter_rows_household_and_3xxx_only():
    rows = [_r("h1", "s1", "3016"), _r("h1", "s2", "1003"), _r("h2", "s3", "3016"), _r("h1", "s4", "1003;3015"),
            _r("h1", "s5", "E31012")]
    out = mod.filter_rows(rows, "h1", COLS)
    assert [r["sessionId"] for r in out] == ["s1", "s4"]
    assert set(out[0]) == set(COLS)


def test_filter_rows_blank_household_raises():
    with pytest.raises(ValueError):
        mod.filter_rows([], "", COLS)
