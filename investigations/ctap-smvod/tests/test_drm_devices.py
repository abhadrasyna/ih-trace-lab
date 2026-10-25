from __future__ import annotations

from pathlib import Path

from conftest import load_script

from lib.drm_devices import (
    br_ref_by_date, outcome_by_kind, rank_failures, widevine_hd_loss, widevine_level_br_ref,
)
from lib.drm_exports import CdmRow, LrmRow, MdrmfeRow

cli = load_script("analyze_mdrm_devices.py")


def _fe(session, fcid, dtype="widevine", br="LOW", hh="H1", content="C1", status="201") -> MdrmfeRow:
    return MdrmfeRow(session, fcid, hh, "D", br, dtype, status, content, "UA")


def _wv(fcid, level) -> CdmRow:
    return CdmRow(fcid, "widevine", "Samsung", "a06", "ANDROID", level, "200")


def test_l1_with_low_br_ref_is_flagged() -> None:
    mdrmfe = [_fe("abr-vod-1", "F1"), _fe("abr-vod-2", "F2", br="HIGH"), _fe("abr-vod-3", "F3")]
    cdm = [_wv("F1", "L1"), _wv("F2", "L1"), _wv("F3", "L3")]
    loss = widevine_hd_loss(mdrmfe, cdm)
    assert (loss.widevine_requests, loss.l1_requests, loss.l1_low_requests) == (3, 2, 1)
    assert (loss.widevine_sessions, loss.l1_low_sessions) == (3, 1)
    assert widevine_level_br_ref(mdrmfe, cdm) == {"L1": {"HIGH": 1, "LOW": 1}, "L3": {"LOW": 1}}


def test_fairplay_low_is_excluded_from_hd_loss_count() -> None:
    mdrmfe = [_fe("abr-vod-1", "F1", dtype="fairplay"), _fe("abr-vod-2", "F2", dtype="playready")]
    cdm = [CdmRow("F1", "fairplay", "Apple", "iPhone", "18.6", "Main", "200")]
    loss = widevine_hd_loss(mdrmfe, cdm)
    assert (loss.widevine_requests, loss.l1_low_requests, loss.l1_low_sessions) == (0, 0, 0)
    assert br_ref_by_date({"d1": mdrmfe, "d2": [_fe("s", "F9", br="HIGH")]})[1] is False


def test_min_volume_threshold_hides_small_groups() -> None:
    mdrmfe = [_fe(f"abr-vod-{i}", f"F{i}", hh="BIG", status="403" if i < 3 else "201") for i in range(6)]
    mdrmfe.append(_fe("abr-vod-x", "FX", hh="SMALL", status="403"))
    lrm = [LrmRow(f"F{i}", "D", "400" if i < 3 else "200") for i in range(6)]
    ranked = rank_failures(mdrmfe, lrm, [], "household", min_volume=5)
    assert [(g.key, g.requests, g.failures) for g in ranked] == [("BIG", 6, 3)]
    assert [g.key for g in rank_failures(mdrmfe, lrm, [], "household", min_volume=1)] == ["BIG", "SMALL"]
    kinds = outcome_by_kind(mdrmfe + [_fe("abr-linear-1", "FL")], lrm + [LrmRow("FL", "D", "200")])
    assert kinds["linear"] == {"success": 1} and kinds["vod"]["failed"] == 4


def test_report_is_written_with_chart(tmp_path: Path) -> None:
    drm = tmp_path / "drm"
    drm.mkdir()
    (drm / "2026-10-23_mdrmfe.csv").write_text(
        "drmAuthToken.sessionId,fcid,drmAuthToken.householdId,drmAuthToken.deviceId,drmAuthToken.brRef,"
        "drmAuthToken.drmType,http.status_code\nabr-vod-1,F1,H,D,LOW,widevine,201\n", encoding="utf-8-sig")
    (drm / "2026-10-23_mdrm-lrm.csv").write_text("fcId,deviceId,http.status_code\nF1,D,200\n", encoding="utf-8-sig")
    (drm / "2026-10-23_mdrm-cdm-widevine.csv").write_text(
        "fcId,drmInfo.Make,drmInfo.Model,drmInfo.Platform,drmInfo.SecurityLevel\nF1,S,m,ANDROID,L1\n", encoding="utf-8-sig")
    path = cli.run("ZA", "2026-10-23", tmp_path / "out", drm)
    text = path.read_text()
    assert "HD loss:** 1 of 1" in text and "constant" in text
    assert (tmp_path / "out" / "ZA" / "charts" / "2026-10-23_mdrm_widevine_level_brref.png").exists()
