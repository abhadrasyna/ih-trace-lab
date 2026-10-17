"""Tests for combine_error_report_1xxx_csv.py."""
from __future__ import annotations

import csv
import sys

import pytest

from conftest import load_script

mod = load_script("combine_error_report_1xxx_csv.py")

COLS = ["sessionId", "error_codes", "position_not_moved", "raw_user_agent"]


def write_source(root, iso, codes):
    d = root / "ZA"
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{iso}_setupsession_with_outcome.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for i, c in enumerate(codes):
            w.writerow({"sessionId": f"{iso}-{i}", "error_codes": c, "position_not_moved": "false", "raw_user_agent": "ua"})


def run(monkeypatch, root, *args):
    monkeypatch.setattr(sys, "argv", ["x", "--output-dir", str(root), "--tenant", "ZA", *args])
    mod.main()


def test_combine_rows_prefixes_date():
    assert mod.combine_rows({"2026-10-01": [{"a": 1}], "2026-10-02": []}) == [{"date": "2026-10-01", "a": 1}]


def test_range_writes_single_csv_with_date_column(tmp_path, monkeypatch):
    write_source(tmp_path, "2026-10-01", ["1003", "6001"])
    write_source(tmp_path, "2026-10-02", ["1002", ""])
    run(monkeypatch, tmp_path, "--from", "01102026", "--to", "02102026", "--columns", "sessionId,error_codes")
    out = next((tmp_path / "ZA").glob("*_error_report_1xxx_combined.csv"))
    rows = list(csv.DictReader(out.open()))
    assert [(r["date"], r["sessionId"]) for r in rows] == [("2026-10-01", "2026-10-01-0"), ("2026-10-02", "2026-10-02-0")]


def test_missing_input_aborts_without_output(tmp_path, monkeypatch, capsys):
    write_source(tmp_path, "2026-10-01", ["1003"])
    with pytest.raises(SystemExit):
        run(monkeypatch, tmp_path, "--from", "01102026", "--to", "02102026")
    assert "2026-10-02_setupsession_with_outcome.csv" in capsys.readouterr().err
    assert not list((tmp_path / "ZA").glob("*combined.csv"))
