"""Tests for run_athena_household_debug_events.py (offline: query building only)."""
from __future__ import annotations

import csv
from types import SimpleNamespace

import pytest

from conftest import load_script

mod = load_script("run_athena_household_debug_events.py")
CTX = SimpleNamespace(debug_events_table="t_ccl_debug_events")


def write_report(path, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["householdId", "deviceId", "sessionId"])
        w.writerows(rows)


def test_load_client_ids_dedupes_and_formats_device_colon_household(tmp_path):
    p = tmp_path / "r.csv"
    write_report(p, [["h1", "d1", "s1"], ["h1", "d1", "s2"], ["", "d2", "s3"]])
    assert mod.load_client_ids(str(p)) == ["d1:h1"]


def test_load_client_ids_rejects_missing_column_empty_and_unsafe(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("householdId,sessionId\nh,s\n")
    with pytest.raises(ValueError):
        mod.load_client_ids(str(p))
    write_report(p, [["", "", "s"]])
    with pytest.raises(ValueError):
        mod.load_client_ids(str(p))
    write_report(p, [["h'; DROP", "d", "s"]])
    with pytest.raises(ValueError):
        mod.load_client_ids(str(p))


def test_date_window_is_inclusive_and_rejects_reversed_range():
    assert mod.date_window("2026-10-01", "2026-10-21") == ("2026-10-01T00:00:00.000Z", "2026-10-22T00:00:00.000Z")
    with pytest.raises(ValueError):
        mod.date_window("2026-10-21", "2026-10-01")


def test_build_query_has_all_events_and_clientid_filter():
    q = mod.build_query(CTX, "db", ["d1:h1", "d2:h2"], "2026-10-01", "2026-10-21")
    assert "'d1:h1'" in q and "'d2:h2'" in q and "eventid =" not in q and "eventid IN" not in q
    assert "datetime <  '2026-10-22T00:00:00.000Z'" in q and '"db"."t_ccl_debug_events"' in q
