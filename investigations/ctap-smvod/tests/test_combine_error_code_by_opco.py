"""Tests for combine_error_code_by_opco.py."""
from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_SPEC = importlib.util.spec_from_file_location("ctap_combine_opco", _SCRIPTS_DIR / "combine_error_code_by_opco.py")
assert _SPEC and _SPEC.loader
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _flat(root: Path, tenant: str, name: str, header: list[str], rows: list[list[str]]) -> None:
    d = root / tenant / mod.FLAT_DIR
    d.mkdir(parents=True, exist_ok=True)
    with open(d / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["x", *argv])
    monkeypatch.setattr(mod, "init_logging", lambda *_: None)
    mod.main()


def _sheet(path: Path, name: str) -> list[list]:
    return [[c.value for c in r] for r in load_workbook(path)[name].iter_rows()]


def test_one_workbook_per_code_with_own_columns(tmp_path, monkeypatch) -> None:
    _flat(tmp_path, "GH", "2026-10-08_6007.csv", ["sessionId", "errorcode"], [["a", "6007"]])
    _flat(tmp_path, "GH", "2026-10-09_1003.csv", ["sessionId", "errorcode", "extra"], [["b", "1003", "x"]])
    _flat(tmp_path, "GH", "2026-10-09_all.csv", ["sessionId", "errorcode"], [["dup", "1003"]])
    _flat(tmp_path, "ZM", "2026-10-11_6007.csv", ["sessionId", "errorcode"], [["c", "6007"]])
    (tmp_path / "SA").mkdir()  # no flat folder -> not a tenant
    _run(monkeypatch, "--output-dir", str(tmp_path))
    f6007 = tmp_path / "error_code" / "6007" / "all_dates_error_6007_by_opco.xlsx"
    f1003 = tmp_path / "error_code" / "1003" / "all_dates_error_1003_by_opco.xlsx"
    assert load_workbook(f6007).sheetnames == ["GH", "ZM"]
    assert load_workbook(f1003).sheetnames == ["GH"]
    assert _sheet(f6007, "GH")[0] == ["date", "sessionId", "errorcode"]
    assert _sheet(f1003, "GH") == [["date", "sessionId", "errorcode", "extra"], ["2026-10-09", "b", "1003", "x"]]
    assert _sheet(f6007, "ZM")[1][0] == "2026-10-11"


def test_date_range_and_codes_filter(tmp_path, monkeypatch) -> None:
    _flat(tmp_path, "GH", "2026-10-07_6007.csv", ["sessionId"], [["old"]])
    _flat(tmp_path, "GH", "2026-10-08_6007.csv", ["sessionId"], [["in"]])
    _flat(tmp_path, "GH", "2026-10-08_1003.csv", ["sessionId"], [["skip"]])
    _run(monkeypatch, "--output-dir", str(tmp_path), "--from", "08102026", "--to", "11102026", "--codes", "6007")
    out = tmp_path / "error_code" / "6007" / "2026-10-08_2026-10-11_error_6007_by_opco.xlsx"
    assert _sheet(out, "GH") == [["date", "sessionId"], ["2026-10-08", "in"]]
    assert not (tmp_path / "error_code" / "1003").exists()


def test_no_matching_files_fails(tmp_path, monkeypatch) -> None:
    _flat(tmp_path, "GH", "2026-10-07_6007.csv", ["sessionId"], [["old"]])
    with pytest.raises(SystemExit):
        _run(monkeypatch, "--output-dir", str(tmp_path), "--from", "01112026")


def test_reversed_range_and_no_tenants_fail(tmp_path, monkeypatch) -> None:
    with pytest.raises(SystemExit):
        _run(monkeypatch, "--output-dir", str(tmp_path), "--from", "11102026", "--to", "08102026")
    with pytest.raises(SystemExit):
        _run(monkeypatch, "--output-dir", str(tmp_path))


def test_list_code_files_ignores_non_matching(tmp_path) -> None:
    _flat(tmp_path, "GH", "2026-10-08_E31012.csv", ["a"], [["1"]])
    (tmp_path / "GH" / mod.FLAT_DIR / "notes.txt").write_text("x")
    files = mod.list_code_files(str(tmp_path / "GH" / mod.FLAT_DIR), date(2026, 10, 8), None)
    assert [(i, c) for i, c, _ in files] == [("2026-10-08", "E31012")]
