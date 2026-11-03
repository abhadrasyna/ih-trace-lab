"""Tests for trace_household_sessions.py (offline)."""
from __future__ import annotations

import pytest
from conftest import load_script

mod = load_script("trace_household_sessions.py")
HH = "vbm1hiRDnFyMXnAku9g2jrgoXLjjWENiDr-N8B1sVAUqXh4HMsE4"


def test_unified_query_filters_on_household_and_date_partition():
    sql = mod.build_unified_query("unified_e6auj7k7", HH, "2026-11-03", "2026-11-03")
    assert f"user_id = '{HH}'" in sql
    assert "BETWEEN '2026-11-03' AND '2026-11-03'" in sql
    assert '"unified_e6auj7k7"."unified_sessions"' in sql and "{{" not in sql


def test_unified_query_rejects_unsafe_household_and_bad_window():
    with pytest.raises(ValueError):
        mod.build_unified_query("unified_e6auj7k7", HH + "' OR '1'='1", "2026-11-03", "2026-11-03")
    with pytest.raises(ValueError):
        mod.parse_utc("03/11/2026")
