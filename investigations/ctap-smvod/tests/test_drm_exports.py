from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib import drm_exports as mod

MDRMFE_HEADER = ("drmAuthToken.sessionId,fcid,drmAuthToken.householdId,drmAuthToken.deviceId,"
                 "drmAuthToken.brRef,drmAuthToken.drmType,http.status_code")


def _write(path: Path, text: str, bom: bool = True) -> None:
    path.write_text(text, encoding="utf-8-sig" if bom else "utf-8")


def test_reads_bom_csv_and_requires_columns(tmp_path: Path) -> None:
    _write(tmp_path / "2026-10-22_mdrmfe.csv", MDRMFE_HEADER + "\nabr-vod-1,F1,H1,D1,LOW,widevine,201\n")
    _write(tmp_path / "2026-10-22_01_mdrmfe.csv", MDRMFE_HEADER + "\nabr-vod-2,F2,H2,D2,HIGH,widevine,201\n")
    rows = mod.read_mdrmfe(tmp_path, "2026-10-22")
    assert [r.session_id for r in rows] == ["abr-vod-1", "abr-vod-2"]
    assert rows[0].br_ref == "LOW" and rows[0].fcid == "F1"

    _write(tmp_path / "2026-10-23_mdrmfe.csv", "drmAuthToken.sessionId,fcid\na,b\n")
    with pytest.raises(ValueError, match="2026-10-23_mdrmfe.csv"):
        mod.read_mdrmfe(tmp_path, "2026-10-23")
    with pytest.raises(FileNotFoundError):
        mod.read_mdrmfe(tmp_path, "2026-10-24")


def test_fairplay_spc_parsed_to_device_and_security_level(tmp_path: Path) -> None:
    spc = json.dumps({"DeviceInfo": "Type:iPhone,OS:26.6.0", "SecurityLevel": "L1"})
    dev = mod.parse_fairplay_spc(spc)
    assert (dev.device_type, dev.os, dev.security_level) == ("iPhone", "26.6.0", "L1")

    quoted = '"' + spc.replace('"', '""') + '"'
    _write(tmp_path / "2026-10-22_mdrm-cdm-fairplay.csv", f"fcId,FP_SPC_contents\nF9,{quoted}\n")
    (row,) = mod.read_cdm(tmp_path, "2026-10-22")
    assert (row.fcid, row.drm_type, row.model, row.platform) == ("F9", "fairplay", "iPhone", "26.6.0")


def test_invalid_fairplay_json_gives_empty_fields() -> None:
    for raw in ("not json", "", "[1, 2]"):
        dev = mod.parse_fairplay_spc(raw)
        assert (dev.device_type, dev.os, dev.security_level) == ("", "", "")
        assert dev.valid is False


def test_unparseable_fairplay_row_warns(tmp_path: Path) -> None:
    _write(tmp_path / "d_mdrm-cdm-fairplay.csv", "fcId,FP_SPC_contents\nF1,garbage\n")
    with pytest.warns(UserWarning, match="unparseable"):
        (row,) = mod.read_cdm(tmp_path, "d")
    assert row.model == ""


def test_widevine_playready_and_lrm_rows(tmp_path: Path) -> None:
    _write(tmp_path / "d_mdrm-cdm-widevine.csv",
           "fcId,drmInfo.Make,drmInfo.Model,drmInfo.Platform,drmInfo.SecurityLevel\nF1,Samsung,a05s,ANDROID,L1\n")
    _write(tmp_path / "d_mdrm-cdm-playready.csv", "fcId,drmInfo.manufacturerName,drmInfo.modelName\nF2,LG,X\n")
    _write(tmp_path / "d_mdrm-lrm.csv", "fcId,deviceId,http.status_code\nF1,D1,200\n")
    cdm = {r.fcid: r for r in mod.read_cdm(tmp_path, "d")}
    assert (cdm["F1"].make, cdm["F1"].model, cdm["F1"].security_level) == ("Samsung", "a05s", "L1")
    assert (cdm["F2"].drm_type, cdm["F2"].make) == ("playready", "LG")
    assert mod.read_lrm(tmp_path, "d")[0].status_code == "200"


def test_cdm_lrm_and_slice_edge_cases(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        mod.read_cdm(tmp_path, "d")
    with pytest.raises(FileNotFoundError):
        mod.read_lrm(tmp_path, "d")
    _write(tmp_path / "d_mdrm-cdm-widevine.csv", "fcId,drmInfo.Make\nF1,Samsung\n")
    with pytest.raises(ValueError, match="d_mdrm-cdm-widevine.csv"):
        mod.read_cdm(tmp_path, "d")
    _write(tmp_path / "d_02_mdrm-lrm.csv", "fcId,deviceId,http.status_code\nF1,D1,200\n")
    _write(tmp_path / "d_01_mdrm-lrm.csv", "fcId,deviceId,http.status_code\nF2,D2,500\n")
    assert [p.name for p in mod.export_paths(tmp_path, "d", mod.LRM)] == ["d_01_mdrm-lrm.csv", "d_02_mdrm-lrm.csv"]
    assert [r.fcid for r in mod.read_lrm(tmp_path, "d")] == ["F2", "F1"]
