"""busUnitId guard for shared Lightstep projects in merge_ctap_smvod_csv.py."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

from conftest import load_script

merge = load_script("merge_ctap_smvod_csv.py")

BUS = "sessionInfo.busUnitId"
ZM_ID = "dtunf6yo"
GH_ID = "apbyfj9d"


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _inputs(folder: Path, ctap_bus: list[str], with_bus: bool = True) -> None:
    extra = [BUS] if with_bus else []
    _write(folder / "2026-10-01_ctap.csv", ["lightstep.trace_id", "http.user_agent"] + extra,
           [[f"t{i}", "ua"] + ([b] if with_bus else []) for i, b in enumerate(ctap_bus)])
    _write(folder / "2026-10-01_smvod.csv", ["lightstep.trace_id", "sessionId"] + extra,
           [[f"t{i}", f"s{i}"] + ([b] if with_bus else []) for i, b in enumerate(ctap_bus)])


def _run(folder: Path, tenant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["merge", "--date", "01102026", "--input-dir", str(folder),
                                      "--out", str(folder / "out.csv"), "--tenant", tenant])
    merge.main()


def test_foreign_busunitid_rows_fail_merge(tmp_path, monkeypatch, capsys):
    _inputs(tmp_path, [ZM_ID, GH_ID])
    with pytest.raises(SystemExit) as exc:
        _run(tmp_path, "ZM", monkeypatch)
    assert exc.value.code == 1
    assert GH_ID in capsys.readouterr().err
    assert not (tmp_path / "out.csv").exists()


def test_missing_busunitid_column_fails_merge(tmp_path, monkeypatch, capsys):
    _inputs(tmp_path, [ZM_ID], with_bus=False)
    with pytest.raises(SystemExit):
        _run(tmp_path, "ZM", monkeypatch)
    assert BUS in capsys.readouterr().err


def test_matching_busunitid_rows_merge(tmp_path, monkeypatch):
    _inputs(tmp_path, [ZM_ID, ZM_ID])
    _run(tmp_path, "ZM", monkeypatch)
    assert (tmp_path / "out.csv").exists()


def test_dedicated_project_tenant_skips_guard(tmp_path, monkeypatch):
    _inputs(tmp_path, [], with_bus=False)
    _write(tmp_path / "2026-10-01_ctap.csv", ["lightstep.trace_id", "http.user_agent"], [["t1", "ua"]])
    _write(tmp_path / "2026-10-01_smvod.csv", ["lightstep.trace_id", "sessionId"], [["t1", "s1"]])
    _run(tmp_path, "SA", monkeypatch)
    assert (tmp_path / "out.csv").exists()
