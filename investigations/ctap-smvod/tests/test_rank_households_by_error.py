"""Tests for rank_households_by_error.py."""
from __future__ import annotations

import sys

import pytest
from openpyxl import Workbook

from conftest import load_script

mod = load_script("rank_households_by_error.py")

HEADER = ["householdId", "deviceId", "sessionId", "error_codes"]


def make_xlsx(path, sheets, header=HEADER):
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(header)
        for r in rows:
            ws.append(r)
    wb.save(path)


def test_csv_input_ranks_and_writes(tmp_path, monkeypatch, capsys):
    c = tmp_path / "2026-10-20_error_report_1xxx.csv"
    c.write_text("householdId,deviceId,sessionId,error_codes,start_time\n"
                 "h1,d1,s1,1001,2026-10-20 05:00:00 UTC\nh1,d1,s2,1003,2026-10-20 06:00:00 UTC\n"
                 "h2,d2,s3,1003,2026-10-20 07:00:00 UTC\n")
    monkeypatch.setattr(sys, "argv", ["x", "--csv", str(c), "--top", "2"])
    mod.main()
    assert (tmp_path / "2026-10-20_error_report_1xxx_household_ranking.csv").exists()
    assert "h1\t2\t1\t1\t1001,1003" in capsys.readouterr().out


def test_csv_missing_column_fails(tmp_path, monkeypatch):
    c = tmp_path / "bad.csv"
    c.write_text("householdId,sessionId\nh1,s1\n")
    monkeypatch.setattr(sys, "argv", ["x", "--csv", str(c)])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


def test_rank_counts_sessions_days_devices(tmp_path, monkeypatch, capsys):
    x = tmp_path / "r.xlsx"
    make_xlsx(x, {
        "2026-10-01": [["h1", "d1", "s1", "1001"], ["h1", "d2", "s2", "1002"], ["h2", "d3", "s3", "1001"]],
        "2026-10-02": [["h1", "d1", "s4", "1001"], ["h1", "d1", "s4", "1001"]],
    })
    ranking = mod.rank_households(mod.load_rows(str(x)))
    assert ranking[0] == {"rank": 1, "householdId": "h1", "sessions": 3, "days": 2, "devices": 2, "error_codes": "1001,1002"}
    assert ranking[1]["householdId"] == "h2" and ranking[1]["sessions"] == 1

    monkeypatch.setattr(sys, "argv", ["x", "--xlsx", str(x), "--top", "1"])
    mod.main()
    assert (tmp_path / "r_household_ranking.csv").exists()
    assert "h1" in capsys.readouterr().out


def test_missing_column_and_blank_household_fail(tmp_path):
    x = tmp_path / "bad.xlsx"
    make_xlsx(x, {"2026-10-01": [["h", "s"]]}, header=["householdId", "sessionId"])
    with pytest.raises(ValueError, match="deviceId, error_codes"):
        mod.load_rows(str(x))
    make_xlsx(x, {"2026-10-01": [["a"]]}, header=["foo"])
    with pytest.raises(ValueError, match="missing column"):
        mod.load_rows(str(x))
    with pytest.raises(ValueError, match="blank"):
        mod.rank_households([{"householdId": "", "sessionId": "s", "date": "d"}])
