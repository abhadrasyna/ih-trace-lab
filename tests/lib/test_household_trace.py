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
    assert row["outcome"] == ht.OUTCOME_LICENSE_OK
    assert ht.device_ids([SM_POST], [MDRMFE]) == ["dev1"]


def test_outcome_without_mdrmfe_or_with_failed_chain_is_flagged():
    rows = ht.build_sessions([SM_POST], [])
    assert ht.classify(rows[SID], False) == ht.OUTCOME_NO_LICENSE
    rows = ht.build_sessions([SM_POST], [MDRMFE])
    ht.attach_chain(rows, [series({"fcId": FCID, "service": "license-request-manager", "http.status_code": "400"})])
    assert ht.classify(rows[SID], False) == ht.OUTCOME_LICENSE_DENIED


def test_athena_error_and_played_override_lightstep_outcome():
    err = ht.summarize_athena([event("PLAYER_ERROR", {"sessionid": SID, "errorcode": 6001, "errordescription": {
        "errordescription": "E86001", "shakaerror": {"message": "REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE"}}})])
    rows = ht.build_sessions([SM_POST], [MDRMFE])
    rows[SID].athena = err[SID]
    assert ht.classify(rows[SID], True) == ht.OUTCOME_FAILED and err[SID]["error_code"] == "6001"
    ok = ht.summarize_athena([event("PLAYER_STATE_CHANGE", {"sessionid": SID, "state": "PLAYING"})])
    rows[SID].athena = ok[SID]
    assert ht.classify(rows[SID], True) == ht.OUTCOME_PLAYED


def test_validate_hhid_and_uql_reject_unsafe_input():
    assert ht.validate_hhid(f" {HH} ") == HH
    for bad in ("short", HH + '" || true', "a b" * 10):
        with pytest.raises(ValueError):
            ht.validate_hhid(bad)
    with pytest.raises(ValueError):
        ht.us_chain_uql(['x" || y'])
    with pytest.raises(ValueError):
        ht.us_chain_uql([])
