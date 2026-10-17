"""Tests for run_athena_debug_sessions.py (offline; no Athena call)."""
from __future__ import annotations

import pytest

from conftest import load_script

mod = load_script("run_athena_debug_sessions.py")


def test_day_bounds_spans_one_utc_day():
    assert mod.day_bounds("2026-10-31") == ("2026-10-31T00:00:00.000Z", "2026-11-01T00:00:00.000Z")


def test_day_bounds_bad_date_raises():
    with pytest.raises(ValueError):
        mod.day_bounds("14-10-2026")
