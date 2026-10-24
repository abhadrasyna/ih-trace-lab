from __future__ import annotations

import csv
from pathlib import Path

import pytest
from conftest import load_script

mod = load_script("run_3016_subcategory_report.py")

FLAT_COLS = ["errorcode", "datetime", "householdId", "deviceId", "sessionId", "pipeline_status", "media_error_type", "user_agent"]


def _write(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def _flat_row(code: str, sid: str, status: str = "") -> dict:
    return {"errorcode": code, "datetime": "2026-10-22 01:00:00", "householdId": "h1", "deviceId": "d1",
            "sessionId": sid, "pipeline_status": status, "media_error_type": "", "user_agent": "Chrome/120"}


def _fixture(tmp_path: Path) -> Path:
    flat = [_flat_row("3016", "s1", "Media failed to decode"), _flat_row("3014", "s2"), _flat_row("6001", "s3")]
    _write(tmp_path / "ZA" / "error_eventdata_flat" / "2026-10-22_all.csv", FLAT_COLS, flat)
    _write(tmp_path / "ZA" / "2026-10-22_setupsession_with_outcome.csv", ["sessionId", "content_uuid"],
           [{"sessionId": "s1", "content_uuid": "c1"}])
    _write(tmp_path / "ZA" / "2026-10-22_position_report.csv", ["sessionId", "max_position"],
           [{"sessionId": "s1", "max_position": "5"}])
    return tmp_path


def test_writes_both_csvs_for_fixture_day(tmp_path: Path) -> None:
    base = _fixture(tmp_path)
    mod.main(["--opco", "ZA", "--date", "2026-10-22", "--base", str(base)])
    out = base / "ZA" / "subcategory_3016"
    events = list(csv.DictReader((out / "2026-10-22_subcategory_events.csv").open()))
    summary = list(csv.DictReader((out / "2026-10-22_subcategory_summary.csv").open()))
    assert len(events) == 2
    assert sum(int(r["events"]) for r in summary) == 2
    assert {r["join_setup"] for r in events} == {"True", "False"}


def test_missing_flat_file_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="flat error file not found"):
        mod.run_day("ZA", "2026-10-22", tmp_path, None)


def test_reconciliation_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="reconciliation failed"):
        mod.reconcile([{}, {}], [{}], [{"events": 1}])


def test_date_range_and_bad_args() -> None:
    assert mod.date_range("2026-10-21", "2026-10-22") == ["2026-10-21", "2026-10-22"]
    with pytest.raises(ValueError):
        mod.date_range("2026-10-22", "2026-10-21")
    with pytest.raises(SystemExit):
        mod.parse_args(["--opco", "ZA"])


def _drm_fixture(drm_dir: Path) -> None:
    drm_dir.mkdir(parents=True, exist_ok=True)
    (drm_dir / "2026-10-22_mdrmfe.csv").write_text(
        "drmAuthToken.sessionId,fcid,drmAuthToken.householdId,drmAuthToken.deviceId,drmAuthToken.brRef,"
        "drmAuthToken.drmType,http.status_code\ns1,F1,H1,D1,LOW,widevine,201\n", encoding="utf-8")
    (drm_dir / "2026-10-22_mdrm-cdm-widevine.csv").write_text(
        "fcId,drmInfo.Make,drmInfo.Model,drmInfo.Platform,drmInfo.SecurityLevel\nF1,Samsung,a05s,ANDROID,L1\n",
        encoding="utf-8")
    (drm_dir / "2026-10-22_mdrm-lrm.csv").write_text(
        "fcId,deviceId,http.status_code\nF1,D1,200\n", encoding="utf-8")


def test_event_row_count_unchanged_with_drm(tmp_path: Path) -> None:
    base = _fixture(tmp_path)
    drm_dir = tmp_path / "drm"
    _drm_fixture(drm_dir)
    mod.main(["--opco", "ZA", "--date", "2026-10-22", "--base", str(base), "--drm", "--drm-dir", str(drm_dir)])
    out = base / "ZA" / "subcategory_3016"
    events = list(csv.DictReader((out / "2026-10-22_subcategory_events.csv").open()))
    device = list(csv.DictReader((out / "2026-10-22_subcategory_device_summary.csv").open()))
    assert len(events) == 2
    assert {r["drm_join"] for r in events} == {"joined", "no_license_request"}
    assert sum(int(r["events"]) for r in device) == 2
    assert any(r["cdm_model"] == "a05s" and r["license_ok"] == "1" for r in device)


def test_drm_missing_export_fails_and_drm_dir_needs_flag(tmp_path: Path) -> None:
    base = _fixture(tmp_path)
    with pytest.raises(FileNotFoundError, match="mdrmfe export"):
        mod.run_day("ZA", "2026-10-22", base, None, tmp_path / "empty")
    with pytest.raises(SystemExit):
        mod.parse_args(["--opco", "ZA", "--date", "2026-10-22", "--drm-dir", "x"])
