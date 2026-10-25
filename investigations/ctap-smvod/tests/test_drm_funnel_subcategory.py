from __future__ import annotations

from pathlib import Path

from conftest import load_script
from test_analyze_drm_funnel import MDRMFE_HEADER, _write_csv

from classify_3016_subcategory import AUDIO, MSE_APPEND, REINIT, UNCATEGORISED
from lib.drm_funnel_subcategory import subcategory_by_session

cli = load_script("analyze_drm_funnel.py")

FLAT_COLS = ["sessionId", "errorcode", "datetime", "householdId", "deviceId", "pipeline_status", "media_error_type"]


def _flat(sid: str, code: str, status: str = "", media: str = "") -> dict:
    return {"sessionId": sid, "errorcode": code, "datetime": "t", "householdId": "H", "deviceId": "D",
            "pipeline_status": status, "media_error_type": media}


def test_subcategory_by_session_uses_first_event_with_the_sessions_code_and_falls_back() -> None:
    flat = [
        _flat("s1", "6001"), _flat("s1", "3016", "video reinitialization failed"),
        _flat("s1", "3016", "audio disconnected"), _flat("s2", "3014"), _flat("s4", "3016", "audio gone"),
    ]
    first = {"s1": "3016", "s2": "3014", "s3": "3016", "s4": "6001", "s5": "3016"}
    out = subcategory_by_session(first, flat, {}, {}, "ZA", "2026-10-23")
    assert out == {"s1": REINIT, "s2": MSE_APPEND, "s3": UNCATEGORISED, "s5": UNCATEGORISED}
    assert AUDIO not in out.values()


def test_padded_ids_and_missing_enrichment_columns_still_classify() -> None:
    flat = [{"sessionId": " s1 ", "errorcode": "3016 ", "pipeline_status": "audio disconnected"}]
    out = subcategory_by_session({"s1": "3016"}, flat, {}, {}, "ZA", "2026-10-23")
    assert out == {"s1": AUDIO}


def test_subcategory_by_license_outcome_for_sample_sessions(tmp_path: Path) -> None:
    base, drm = tmp_path / "output", tmp_path / "drm"
    _write_csv(base / "ZA" / "2026-10-23_setupsession_with_outcome.csv", ["sessionId", "error_codes"], [
        {"sessionId": "abr-vod-1", "error_codes": "3016"}, {"sessionId": "abr-vod-2", "error_codes": "3016"},
        {"sessionId": "abr-vod-3", "error_codes": "3014"}, {"sessionId": "abr-vod-4", "error_codes": ""},
    ])
    _write_csv(base / "ZA" / "error_eventdata_flat" / "2026-10-23_all.csv", FLAT_COLS, [
        _flat("abr-vod-1", "3016", "audio decode failed"), _flat("abr-vod-2", "3016", "Video reinitialization failed"),
        _flat("abr-vod-3", "3014"),
    ])
    drm.mkdir()
    (drm / "2026-10-23_mdrmfe.csv").write_text(
        MDRMFE_HEADER + "\nabr-vod-1,F1,H,D,LOW,widevine,201\nabr-vod-2,F2,H,D,LOW,widevine,403\n",
        encoding="utf-8-sig")
    (drm / "2026-10-23_mdrm-lrm.csv").write_text("fcId,deviceId,http.status_code\nF1,D,200\nF2,D,400\n",
                                                 encoding="utf-8-sig")
    cli.run("ZA", "2026-10-23", base, drm)
    md = (base / "ZA" / "drm-analysis" / "2026-10-23_drm_funnel.md").read_text()
    section = md.split("## 3014/3015/3016 by sub-category")[1]
    assert f"| {AUDIO} | 1 | 1 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |" in section
    assert f"| {REINIT} | 1 | 0 (0.0%) | 0 (0.0%) | 1 (100.0%) | 0 (0.0%) |" in section
    assert f"| {MSE_APPEND} | 1 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 1 (100.0%) |" in section


def test_subcategory_sessions_reconcile_to_3016_table(tmp_path: Path) -> None:
    base, drm = tmp_path / "output", tmp_path / "drm"
    _write_csv(base / "ZA" / "2026-10-23_setupsession_with_outcome.csv", ["sessionId", "error_codes"], [
        {"sessionId": f"abr-vod-{i}", "error_codes": code}
        for i, code in enumerate(["3016", "3016", "3015", "6001", ""], start=1)
    ])
    drm.mkdir()
    (drm / "2026-10-23_mdrmfe.csv").write_text(MDRMFE_HEADER + "\n", encoding="utf-8-sig")
    (drm / "2026-10-23_mdrm-lrm.csv").write_text("fcId,deviceId,http.status_code\n", encoding="utf-8-sig")
    result = cli.run("ZA", "2026-10-23", base, drm)
    named = sum(r.sessions for r in result.rows if r.error_code in ("3014", "3015", "3016"))
    with_sub = sum(r.sessions for r in result.rows if r.subcategory)
    assert named == with_sub == 3
    assert all(not r.subcategory for r in result.rows if r.error_code not in ("3014", "3015", "3016"))
    md = (base / "ZA" / "drm-analysis" / "2026-10-23_drm_funnel.md").read_text()
    assert "Total: 3 sessions" in md
