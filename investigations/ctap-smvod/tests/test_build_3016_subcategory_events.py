from __future__ import annotations

from conftest import load_script

mod = load_script("build_3016_subcategory_events.py")

UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36"
UUID = "4b648d62-6fd0-5d50-9840-0123456789ab"


def _err(sid="s1", hh="h1", code="3016", status="PipelineStatus::Media failed to decode", ua=UA) -> dict:
    return {
        "errorcode": code, "pipeline_status": status, "media_error_type": "", "datetime": "2026-10-22T10:00:00Z",
        "householdId": hh, "deviceId": "d1", "sessionId": sid, "position": "12.5", "player_phase": "playing",
        "user_agent": ua,
    }


def test_join_by_session_adds_content_and_keeps_raw_user_agent() -> None:
    setup = {"s1": {"content_uuid": UUID, "externalPackageId": "pkg", "OS Family": "Android", "OS Version": "10"}}
    pos = {"s1": {"max_position": "99"}}
    [row] = mod.build_events([_err()], setup, pos, "ZA", "2026-10-22")
    assert row["content_uuid"] == UUID
    assert row["externalPackageId"] == "pkg"
    assert row["os"] == "Android 10"
    assert row["session_max_position"] == "99"
    assert row["join_setup"] and row["join_position"]
    assert row["user_agent"] == UA
    assert row["browser"] == "Chrome 125"
    assert row["device_model"] == "K"
    assert row["subcategory"] == "Video decode error"


def test_empty_session_or_household_never_joins_or_counts() -> None:
    setup = {"": {"content_uuid": UUID}}
    errors = [_err(sid="", hh=""), _err(sid="", hh="")]
    rows = mod.build_events(errors, setup, {"": {}}, "ZA", "2026-10-22")
    for r in rows:
        assert not r["join_setup"] and not r["join_position"]
        assert r["content_uuid"] == ""
        assert r["hh_repeat_events"] == 0
        assert r["content_distinct_hh"] == 0


def test_unknown_content_never_counts_as_shared_content() -> None:
    errors = [_err(sid="a", hh="h1"), _err(sid="b", hh="h2")]
    rows = mod.build_events(errors, {}, {}, "ZA", "2026-10-22")
    assert all(r["content_uuid"] == "" and r["content_distinct_hh"] == 0 for r in rows)


def test_segment_url_parsed_for_vode_and_vodc() -> None:
    for kind in ("vode", "vodc"):
        status = f"https://cdn.example/x/{kind}/{UUID}/3/seg_12.m4s"
        [row] = mod.build_events([_err(code="3014", status=status)], {}, {}, "ZA", "2026-10-22")
        assert row["content_uuid"] == UUID
        assert row["segment_file"] == "seg_12.m4s"
        assert row["subcategory"] == "MSE append failed (3014/3015)"
