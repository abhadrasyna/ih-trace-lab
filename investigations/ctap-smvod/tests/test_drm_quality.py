from __future__ import annotations

from pathlib import Path

from conftest import load_script

from lib.drm_exports import CdmRow, LrmRow, MdrmfeRow
from lib.drm_quality import (
    duplicate_fcids_across_parts, failing_requests, fcid_chain, layer_overlap, repeat_failures, requests_per_key,
    status_counts, whole_day_with_parts,
)

cli = load_script("analyze_mdrm_quality.py")


def _fe(session, fcid, hh="H1", dev="D1", status="201", dtype="widevine") -> MdrmfeRow:
    return MdrmfeRow(session, fcid, hh, dev, "LOW", dtype, status, "C1", "UA")


def test_counts_failures_and_joins_by_fcid() -> None:
    mdrmfe = [_fe("s1", "F1"), _fe("s2", "F2", status="403"), _fe("s3", "F3")]
    lrm = [LrmRow("F1", "D1", "200"), LrmRow("F2", "D1", "400"), LrmRow("F3", "D9", "400"), LrmRow("F4", "D1", "200")]
    cdm = [CdmRow("F1", "widevine", "S", "m", "ANDROID", "L1", "200")]
    counts = {(c.export, c.drm_type, c.status): c.count for c in status_counts(mdrmfe, lrm, cdm)}
    assert counts[("mdrmfe", "widevine", "403")] == 1 and counts[("lrm", "widevine", "400")] == 2
    assert counts[("lrm", "unknown", "200")] == 1 and counts[("cdm", "widevine", "200")] == 1
    failures = {f.fcid: f for f in failing_requests(mdrmfe, lrm)}
    assert failures["F2"].layers == "mdrmfe+lrm" and failures["F3"].layers == "lrm"
    assert failures["F3"].session_id == "s3" and failures["F3"].content_id == "C1"
    assert layer_overlap(list(failures.values())) == {"mdrmfe+lrm": 1, "mdrmfe": 0, "lrm": 1}
    chain = fcid_chain(mdrmfe, lrm, cdm)
    assert chain.mdrmfe_not_in_cdm == 2 and chain.lrm_not_in_mdrmfe == 1 and chain.cdm_not_in_mdrmfe == 0
    assert chain.device_mismatches == [("F3", "D1", "D9")]


def test_flags_duplicate_fcid_across_parts_and_missing_chain_rows() -> None:
    parts = {"d_01_mdrm-lrm.csv": ["A", "B"], "d_02_mdrm-lrm.csv": ["B", "C"]}
    assert duplicate_fcids_across_parts(parts) == {"B": ["d_01_mdrm-lrm.csv", "d_02_mdrm-lrm.csv"]}
    assert duplicate_fcids_across_parts({"only.csv": ["A", "A"]}) == {}
    names = ["2026-10-23_mdrmfe.csv", "2026-10-23_01_mdrmfe.csv"]
    assert "coexists" in whole_day_with_parts(names, "2026-10-23", "mdrmfe")
    assert whole_day_with_parts(names[:1], "2026-10-23", "mdrmfe") == ""
    chain = fcid_chain([_fe("s1", "F1"), _fe("s2", "F2")], [LrmRow("F1", "D1", "200")], [])
    assert chain.mdrmfe_not_in_lrm == 1 and chain.mdrmfe_not_in_lrm_ok == 1


def test_repeat_failures_by_device_household_and_session() -> None:
    mdrmfe = [_fe("s1", "F1", status="403"), _fe("s1", "F2", status="403"), _fe("s2", "F3", hh="H2", status="403")]
    repeats = repeat_failures(failing_requests(mdrmfe, []))
    assert repeats["session_id"] == [("s1", 2)]
    assert repeats["device_id"] == [("D1", 3)] and repeats["household_id"] == [("H1", 2)]
    assert requests_per_key(mdrmfe, "session_id") == {1: 1, 2: 1}


def test_report_writes_markdown_and_failures_csv(tmp_path: Path) -> None:
    drm = tmp_path / "drm"
    drm.mkdir()
    (drm / "2026-10-23_mdrmfe.csv").write_text(
        "drmAuthToken.sessionId,fcid,drmAuthToken.householdId,drmAuthToken.deviceId,drmAuthToken.brRef,"
        "drmAuthToken.drmType,http.status_code\ns1,F1,H,D,LOW,widevine,403\n", encoding="utf-8-sig")
    (drm / "2026-10-23_mdrm-lrm.csv").write_text("fcId,deviceId,http.status_code\nF1,D,400\n", encoding="utf-8-sig")
    (drm / "2026-10-23_mdrm-cdm-widevine.csv").write_text(
        "fcId,drmInfo.Make,drmInfo.Model,drmInfo.Platform,drmInfo.SecurityLevel\nF1,S,m,ANDROID,L1\n", encoding="utf-8-sig")
    failures = cli.run("ZA", "2026-10-23", tmp_path / "out", drm)
    assert len(failures) == 1
    assert "1 distinct fcId" in (tmp_path / "out" / "ZA" / "2026-10-23_mdrm_quality.md").read_text()
    assert "F1" in (tmp_path / "out" / "ZA" / "2026-10-23_mdrm_quality_failures.csv").read_text()
