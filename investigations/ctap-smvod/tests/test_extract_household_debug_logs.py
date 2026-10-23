"""Tests for extract_household_debug_logs.py."""
from __future__ import annotations

import csv
import sys

import pytest

from conftest import load_script

mod = load_script("extract_household_debug_logs.py")


def write_csv(path, header, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def test_load_session_map_and_missing_column(tmp_path):
    p = tmp_path / "r.csv"
    write_csv(p, ["householdId", "deviceId", "sessionId"], [["h", "d", "s1"]])
    assert mod.load_session_map(str(p)) == {"s1": {"householdId": "h", "deviceId": "d"}}
    write_csv(p, ["householdId", "sessionId"], [["h", "s1"]])
    with pytest.raises(ValueError):
        mod.load_session_map(str(p))


def test_filter_debug_rows_keeps_only_mapped_sessions():
    rows = [{"sessionId": "s1", "state": "CREATE", "datetime": "t"}, {"sessionId": "x", "state": "CREATE"}]
    out = mod.filter_debug_rows(rows, {"s1": {"householdId": "h", "deviceId": "d"}}, "f.csv")
    assert len(out) == 1 and out[0]["householdId"] == "h" and out[0]["source_file"] == "f.csv"


def test_blank_session_id_skipped_and_missing_debug_column_rejected(tmp_path):
    p = tmp_path / "r.csv"
    write_csv(p, ["householdId", "deviceId", "sessionId"], [["h", "d", ""], ["h", "d", "s1"]])
    assert list(mod.load_session_map(str(p))) == ["s1"]
    d = tmp_path / "d.csv"
    write_csv(d, ["sessionId", "state", "dateTime"], [["s1", "CREATE", "1"]])
    with pytest.raises(ValueError):
        mod.read_csv_rows(str(d))


def test_main_writes_sorted_output_and_fails_without_matches(tmp_path, monkeypatch):
    report = tmp_path / "rep.csv"
    write_csv(report, ["householdId", "deviceId", "sessionId"], [["h", "d", "s1"]])
    data = tmp_path / "data"
    data.mkdir()
    hdr = ["sessionId", "eventid", "state", "position", "errorcode", "errordescription", "datetime"]
    write_csv(data / "2026-10-18_debug_states.csv", hdr,
              [["s1", "e", "ERROR", "", "3016", "", "2"], ["s1", "e", "CREATE", "", "", "", "1"], ["zz", "e", "X", "", "", "", "0"]])
    monkeypatch.setattr(sys, "argv", ["x", "--report-csv", str(report), "--tenant", "ZA", "--data-dir", str(data)])
    mod.main()
    out = list(csv.DictReader((tmp_path / "rep_debug_logs.csv").open()))
    assert [r["state"] for r in out] == ["CREATE", "ERROR"]

    write_csv(report, ["householdId", "deviceId", "sessionId"], [["h", "d", "nomatch"]])
    with pytest.raises(SystemExit):
        mod.main()
