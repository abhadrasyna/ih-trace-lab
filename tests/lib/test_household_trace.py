"""Tests for scripts/lib/household_trace.py (offline, pure logic)."""
from __future__ import annotations

import json

import pytest

from scripts.lib import household_trace as ht

HH = "vbm1hiRDnFyMXnAku9g2jrgoXLjjWENiDr-N8B1sVAUqXh4HMsE4"
SID = "abr-vod-58f93a61-8b9f-4cdf-bdab-df4dca533fda"
FCID = "6AE9E6ADAF4E61290001752A"


def series(labels_, ms=1793713860000):
    return {"group-labels": [f"{k}={v}" for k, v in labels_.items()], "points": [[ms, 1]]}


SM_POST = series({"sessionId": SID, "operation": "POST", "http.status_code": "200", "deviceId": "dev1",
                  "contentId": "c1", "session.clientIp": "1.2.3.4"})
SM_DEL = series({"sessionId": SID, "operation": "DELETE", "http.status_code": "204"}, 1793713920000)
MDRMFE = series({"drmAuthToken.sessionId": SID, "drmAuthToken.drmType": "widevine", "drmAuthToken.brRef": "LOW",
                 "http.status_code": "201", "fcid": FCID, "drmAuthToken.deviceId": "dev1"})
US_OK = [series({"fcId": FCID, "service": "license-request-manager", "http.status_code": "200"}),
         series({"fcId": FCID, "service": "widevine-license-generator", "http.status_code": "200",
                 "drmInfo.Make": "Samsung", "drmInfo.Model": "r12s", "drmInfo.Platform": "ANDROID",
                 "drmInfo.SecurityLevel": "L1"})]


def event(eid, data):
    return {"eventid": eid, "eventdata": json.dumps(data)}


def test_session_joins_sm_vod_mdrmfe_and_us_chain_and_reports_device():
    rows = ht.build_sessions([SM_POST, SM_DEL], [MDRMFE])
    ht.attach_chain(rows, US_OK)
    row = ht.to_table(rows, False, lambda ms: str(ms))[0]
    assert (row["sm_vod_create"], row["sm_vod_teardown"], row["brRef"], row["fcid"]) == ("200", "204", "LOW", FCID)
    assert (row["drm_make"], row["drm_model"], row["drm_security_level"]) == ("Samsung", "r12s", "L1")
    assert row["outcome"] == ht.OUTCOME_MDRM_LICENSE_OK_NO_ATHENA and row["evidence_layer"] == "MDRM"
    assert ht.device_ids([SM_POST], [MDRMFE]) == ["dev1"]


def test_outcome_without_mdrmfe_or_with_failed_chain_is_flagged():
    rows = ht.build_sessions([SM_POST], [])
    assert ht.classify(rows[SID], False) == ht.OUTCOME_MDRMFE_SPAN_NOT_SEEN
    rows = ht.build_sessions([SM_POST], [MDRMFE])
    ht.attach_chain(rows, [series({"fcId": FCID, "service": "license-request-manager", "http.status_code": "400"})])
    assert ht.classify(rows[SID], False) == ht.OUTCOME_MDRM_US_HOP_NON_2XX


def test_sm_vod_create_failure_wins_over_missing_mdrmfe_span():
    post_500 = series({"sessionId": SID, "operation": "POST", "http.status_code": "500"})
    row = ht.to_table(ht.build_sessions([post_500], []), False, str)[0]
    assert (row["outcome"], row["evidence_layer"]) == (ht.OUTCOME_SMVOD_CREATE_NON_2XX, "SMVOD")


def test_mdrmfe_failure_is_not_blamed_on_us_hop_and_every_outcome_has_a_layer():
    fe_403 = series({"drmAuthToken.sessionId": SID, "http.status_code": "403", "fcid": FCID})
    rows = ht.build_sessions([SM_POST], [fe_403])
    assert ht.classify(rows[SID], False) == ht.OUTCOME_MDRMFE_STATUS_NON_2XX
    outcomes = {v for k, v in vars(ht).items() if k.startswith("OUTCOME_")}
    assert outcomes == set(ht.EVIDENCE_LAYER)


def unified(event_type, start, end, endreason, device="dev1", title="Boss Level"):
    return {"parent_session_id": SID, "device_id": device, "event_type": event_type, "event_start": start, "event_end": end,
            "content": title, "content_id": "AXP9000000030", "endreason": endreason}


def test_unified_sessions_give_title_play_time_and_outcome():
    played = ht.summarize_unified([
        unified("REQUEST_VIEWING", "2026-11-03 13:50:34.746", "2026-11-03 13:50:38.641", "PLAYING"),
        unified("PLAY", "2026-11-03 13:50:34.746", "2026-11-03 13:51:21.342", "DESTROY"),
    ])
    rows = ht.build_sessions([SM_POST], [MDRMFE])
    rows[SID].unified = played[SID]
    row = ht.to_table(rows, True, str)[0]
    assert (row["content_title"], row["unified_endreason"], row["play_seconds"]) == ("Boss Level", "DESTROY", "47")
    assert (row["outcome"], row["evidence_layer"]) == (ht.OUTCOME_ATHENA_SESSION_PLAYED, "ATHENA")


def test_unified_player_error_and_unknown_session_fall_back():
    failed = ht.summarize_unified([unified("REQUEST_VIEWING", "2026-11-03 13:31:37.766", "2026-11-03 13:31:40.135", "PLAYER_ERROR")])
    rows = ht.build_sessions([SM_POST], [MDRMFE])
    assert ht.classify(rows[SID], True) == ht.OUTCOME_MDRM_LICENSE_OK_NO_ATHENA  # not in unified_sessions
    rows[SID].unified = failed[SID]
    assert ht.classify(rows[SID], True) == ht.OUTCOME_ATHENA_SESSION_PLAYER_ERROR
    assert ht.summarize_unified([{"event_type": "PLAY"}]) == {}


def test_debug_events_are_requested_only_for_errored_sessions_by_month():
    other = "abr-vod-other"
    rows = ht.build_sessions([SM_POST], [])
    rows[SID].unified = ht.summarize_unified([unified("REQUEST_VIEWING", "2026-11-03 13:31:37", "2026-11-03 13:31:40", "PLAYER_ERROR")])[SID]
    rows[other] = ht.SessionRow(other, unified={"endreason": "DESTROY", "device_id": "dev2", "first_start": "2026-11-03 13:50:00"})
    groups = ht.error_sessions_by_table(rows, None, ["oct26", "sept26"])
    assert groups == {"": {"devices": ["dev1"], "date_from": "2026-11-03", "date_to": "2026-11-03", "sessions": [SID]}}
    assert list(ht.error_sessions_by_table(rows, "oct26", [])) == ["oct26"]
    assert ht.pick_debug_suffix("2026-09-30 10:00:00", ["oct26", "sept26"]) == "sept26"
    assert ht.pick_debug_suffix("2026-10-19 10:00:00", ["oct26", "sept26"]) == "oct26"
    rows[SID].unified["device_id"] = ""
    with pytest.raises(ValueError):
        ht.error_sessions_by_table(rows, None, [])


def test_debug_events_summary_keeps_first_player_error_detail():
    err = ht.summarize_athena([event("PLAYER_ERROR", {"sessionid": SID, "errorcode": 6001, "errordescription": {
        "errordescription": "E86001", "shakaerror": {"message": "REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE"}}})])
    assert err[SID]["error_code"] == "6001" and err[SID]["shaka_error"] == "REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE"


def test_validate_hhid_and_uql_reject_unsafe_input():
    assert ht.validate_hhid(f" {HH} ") == HH
    for bad in ("short", HH + '" || true', "a b" * 10):
        with pytest.raises(ValueError):
            ht.validate_hhid(bad)
    with pytest.raises(ValueError):
        ht.us_chain_uql(['x" || y'])
    with pytest.raises(ValueError):
        ht.us_chain_uql([])
