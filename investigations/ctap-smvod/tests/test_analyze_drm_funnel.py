from __future__ import annotations

import csv
from pathlib import Path

import pytest
from conftest import load_script

mod = load_script("analyze_drm_funnel.py")

MDRMFE_HEADER = ("drmAuthToken.sessionId,fcid,drmAuthToken.householdId,drmAuthToken.deviceId,"
                 "drmAuthToken.brRef,drmAuthToken.drmType,http.status_code")


def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def _inputs(tmp_path: Path, with_mdrm: bool = True) -> tuple[Path, Path]:
    base, drm = tmp_path / "output", tmp_path / "drm"
    _write_csv(base / "ZA" / "2026-10-23_setupsession_with_outcome.csv", ["sessionId", "error_codes"], [
        {"sessionId": "abr-vod-1", "error_codes": ""},
        {"sessionId": "abr-vod-2", "error_codes": "3016"},
        {"sessionId": "abr-vod-3", "error_codes": ""},
    ])
    _write_csv(base / "ZA" / "error_eventdata_flat" / "2026-10-23_all.csv", ["sessionId", "errorcode"],
               [{"sessionId": "abr-vod-3", "errorcode": "6001"}])
    if with_mdrm:
        drm.mkdir()
        (drm / "2026-10-23_mdrmfe.csv").write_text(
            MDRMFE_HEADER + "\nabr-vod-1,F1,H,D,LOW,widevine,201\nabr-vod-2,F2,H,D,LOW,fairplay,403\n"
            "abr-vod-9,F9,H,D,LOW,widevine,201\n", encoding="utf-8-sig")
        (drm / "2026-10-23_mdrm-lrm.csv").write_text(
            "fcId,deviceId,http.status_code\nF1,D,200\nF2,D,400\nF9,D,200\n", encoding="utf-8-sig")
    return base, drm


def test_writes_csv_and_markdown_for_sample_inputs(tmp_path: Path) -> None:
    base, drm = _inputs(tmp_path)
    result = mod.run("ZA", "2026-10-23", base, drm)

    assert result.totals == {"sessions": 4, "drm_requested": 3, "license_success": 2, "license_failed": 1,
                             "errored": 2, "drm_only": 1}
    rows = list(csv.DictReader((base / "ZA" / "2026-10-23_drm_funnel.csv").open()))
    assert sum(int(r["sessions"]) for r in rows) == 4
    assert {r["source"] for r in rows} == {"merge", "drm_only"}
    md = (base / "ZA" / "2026-10-23_drm_funnel.md").read_text()
    assert "# DRM funnel — ZA — 2026-10-23" in md
    assert "`source=drm_only`" in md and "License outcome per DRM type" in md


def test_missing_mdrm_export_raises_with_file_name(tmp_path: Path) -> None:
    base, drm = _inputs(tmp_path, with_mdrm=False)
    drm.mkdir()
    with pytest.raises(FileNotFoundError, match="2026-10-23_mdrmfe.csv"):
        mod.run("ZA", "2026-10-23", base, drm)


def test_missing_merge_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="2026-10-23_setupsession_with_outcome.csv"):
        mod.run("ZA", "2026-10-23", tmp_path / "output", tmp_path / "drm")


def test_missing_flat_error_file_is_optional(tmp_path: Path) -> None:
    base, drm = _inputs(tmp_path)
    (base / "ZA" / "error_eventdata_flat" / "2026-10-23_all.csv").unlink()
    assert mod.run("ZA", "2026-10-23", base, drm).totals["errored"] == 1


def test_3016_table_splits_by_license_outcome(tmp_path: Path) -> None:
    base, drm = _inputs(tmp_path)
    mod.run("ZA", "2026-10-23", base, drm)
    md = (base / "ZA" / "2026-10-23_drm_funnel.md").read_text()
    assert "counted under its first error code only" in md
    assert "| 3016 | 1 | 0 (0.0%) | 0 (0.0%) | 1 (100.0%) | 0 (0.0%) |" in md
    assert "| 3014 | 0 |" in md
    assert "Reading: most 3016 sessions had license outcome `failed` (100.0%)." in md
    assert "| 6001 | 1 | 50.0% |" in md
    rows = list(csv.DictReader((base / "ZA" / "2026-10-23_drm_funnel.csv").open()))
    assert {r["error_code"] for r in rows} == {"none", "3016", "6001"}
