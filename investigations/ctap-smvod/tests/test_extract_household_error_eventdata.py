"""Tests for extract_household_error_eventdata.py."""
from __future__ import annotations

import csv
import json
import sys

import pytest

from conftest import load_script

mod = load_script("extract_household_error_eventdata.py")
HDR = ["datetime", "messageid", "clientid", "eventclass", "eventid", "eventdata"]


def write_csv(path, header, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def ev(dt, sid):
    return [dt, "m", "c", "PLAYER", "PLAYER_ERROR", json.dumps({"sessionid": sid})]


def test_load_session_map_skips_blank_and_rejects_missing_column(tmp_path):
    p = tmp_path / "r.csv"
    write_csv(p, ["householdId", "deviceId", "sessionId"], [["h", "d", ""], ["h", "d", "s1"]])
    assert mod.load_session_map(str(p)) == {"s1": {"householdId": "h", "deviceId": "d"}}
    write_csv(p, ["householdId", "sessionId"], [["h", "s1"]])
    with pytest.raises(ValueError):
        mod.load_session_map(str(p))


def test_filter_rows_matches_on_eventdata_sessionid():
    rows = [dict(zip(HDR, ev("t", "s1"))), dict(zip(HDR, ev("t", "x")))]
    out = mod.filter_rows(rows, {"s1": {"householdId": "h", "deviceId": "d"}}, "f.csv")
    assert len(out) == 1 and out[0]["sessionId"] == "s1" and out[0]["deviceId"] == "d"


def test_invalid_eventdata_json_and_missing_column_fail_loudly(tmp_path):
    with pytest.raises(ValueError):
        mod.session_id_of({"eventdata": "{not json"})
    d = tmp_path / "d.csv"
    write_csv(d, ["datetime", "eventdata"], [["1", "{}"]])
    with pytest.raises(ValueError):
        mod.read_csv_rows(str(d))


def test_main_writes_sorted_output_and_fails_without_matches(tmp_path, monkeypatch):
    report = tmp_path / "rep.csv"
    write_csv(report, ["householdId", "deviceId", "sessionId"], [["h", "d", "s1"]])
    data = tmp_path / "data"
    data.mkdir()
    write_csv(data / "2026-10-18_error_eventdata.csv", HDR, [ev("2", "s1"), ev("1", "s1"), ev("0", "zz")])
    monkeypatch.setattr(sys, "argv", ["x", "--report-csv", str(report), "--tenant", "ZA", "--data-dir", str(data)])
    mod.main()
    out = list(csv.DictReader((tmp_path / "rep_error_eventdata.csv").open()))
    assert [r["datetime"] for r in out] == ["1", "2"]

    write_csv(report, ["householdId", "deviceId", "sessionId"], [["h", "d", "nomatch"]])
    with pytest.raises(SystemExit):
        mod.main()
