"""Tests for flatten_error_eventdata.py."""
from __future__ import annotations

import json

import pytest

from conftest import load_script

mod = load_script("flatten_error_eventdata.py")

SHAKA_3016 = {"severity": 2, "category": 3, "code": 3016, "data": [3, None, "PipelineStatus::PIPELINE_ERROR_DECODE"],
              "message": "Shaka Error MEDIA.VIDEO_ERROR"}
INNER_BODY = json.dumps({"type": "https://dashif.org/drm-problems/device-insufficient-security-level",
                         "title": "Not Authorized", "status": 403,
                         "detail": 'MDRM server returned 400, body: "{\\"code\\":\\"6211\\",\\"message\\":\\"Test device not allowed\\"}"'})
SHAKA_6007 = {"code": 6007, "category": 6,
              "message": "Shaka Error DRM.LICENSE_REQUEST_FAILED (shaka.util.Error {\n  \"code\": 1001\n})", "data": [
    {"code": 1001, "message": "Shaka Error NETWORK.BAD_HTTP_STATUS (https://lic.example/widevine/x,403)",
     "stack": "Error\n at https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.12.6/shaka-player.ui.debug.js:1:1",
     "data": ["https://lic.example/widevine/x", 403, INNER_BODY, {"flow_context": "FC123"}, 2,
              "https://lic.example/widevine/x"]}]}


def _row(mid: str, errorcode, shaka: dict, ua: str = "Mozilla/5.0 (Linux; Android 10; K) Chrome/150") -> dict[str, str]:
    payload = {"position": 1.5, "sessionid": f"abr-vod-{mid}", "errorcode": errorcode, "errordescription": {
        "errordescription": "E8 : text", "user_agent": ua, "shakaerror": shaka, "app_version": "v1",
        "playerstatesnapshot": {"phase": "SEEKING", "isbuffering": False},
        "networkdetails": {"navigatorconnection": {"type": "CELLULAR", "effectivetype": "3g"},
                           "shakastats": {"streambandwidthmbps": 0.35, "bufferingtime": 2.5}, "drmdiagnostics": None}}}
    return {"datetime": "2026-10-04T19:00:00.000Z", "messageid": mid, "clibversion": "JS.1.7.0",
            "clientid": "dev1:hh1", "eventdata": json.dumps(payload)}


def test_flatten_3016_columns():
    flat = mod.flatten_row(_row("a", 3016, SHAKA_3016))
    assert flat["deviceId"] == "dev1" and flat["householdId"] == "hh1"
    assert flat["shaka_code"] == 3016 and flat["player_phase"] == "SEEKING"
    assert flat["net_effectivetype"] == "3g" and flat["stream_mbps"] == 0.35
    assert flat["is_wv"] == "false" and flat["drm_present"] == "false"
    assert set(flat) == set(mod.FIELDS)


def test_flatten_6007_nested_drm_error():
    flat = mod.flatten_row(_row("b", 6007, SHAKA_6007))
    assert flat["nested_shaka_code"] == 1001 and flat["nested_http_status"] == 403
    assert flat["nested_title"] == "Not Authorized" and flat["nested_mdrm_code"] == "6211"
    assert flat["shaka_url"] == "https://lic.example/widevine/x" and flat["shaka_url_host"] == "lic.example"
    assert flat["shaka_error_name"] == "DRM.LICENSE_REQUEST_FAILED"
    assert flat["shaka_message"] == "Shaka Error DRM.LICENSE_REQUEST_FAILED" and "\n" not in flat["shaka_message"]
    assert flat["nested_error_name"] == "NETWORK.BAD_HTTP_STATUS"
    assert flat["nested_problem_type"] == "device-insufficient-security-level"
    assert flat["nested_mdrm_http_status"] == "400" and flat["nested_mdrm_message"] == "Test device not allowed"
    assert flat["flow_context"] == "FC123" and flat["shaka_version"] == "4.12.6"


def test_flatten_null_nested_fields_do_not_crash():
    body = json.dumps({"type": None, "title": None, "detail": None})
    shaka = {"code": 6007, "message": None, "data": [{"code": 1001, "message": None, "stack": None,
                                                       "data": ["https://x.example/a", 403, body, {"flow_context": None}]}]}
    flat = mod.flatten_row(_row("n", 6007, shaka))
    assert flat["nested_problem_type"] == "" and flat["flow_context"] == "" and flat["shaka_message"] == ""


def test_split_by_errorcode_drops_blank_columns_per_code():
    shaka_stats = {"estimatedbandwidth": 100.5, "lastswitch": {"id": 2, "type": "variant", "bandwidth": 345614}}
    row3016 = _row("a", 3016, SHAKA_3016)
    payload = json.loads(row3016["eventdata"])
    payload["errordescription"]["networkdetails"]["shakastats"].update(shaka_stats)
    row3016["eventdata"] = json.dumps(payload)
    flat = mod.flatten_rows([row3016, _row("b", 6007, SHAKA_6007)])
    split = mod.split_by_errorcode(flat)
    cols3016, rows3016 = split["3016"]
    cols6007, _ = split["6007"]
    assert rows3016[0]["pipeline_status"] == "PipelineStatus::PIPELINE_ERROR_DECODE"
    assert rows3016[0]["media_error_type"] == 3 and rows3016[0]["lastswitch_type"] == "variant"
    assert "nested_mdrm_code" not in cols3016 and "pipeline_status" not in cols6007
    assert "nested_mdrm_code" in cols6007 and "raw_eventdata" in cols3016


def test_split_keeps_false_booleans():
    split = mod.split_by_errorcode(mod.flatten_rows([_row("a", 3016, SHAKA_3016)]))
    assert "player_isbuffering" in split["3016"][0]


def test_flatten_1003_timeout_has_blank_nested_and_name():
    timeout = {"code": 1003, "category": 1, "data": ["https://cdn.example/seg.m4f", 1],
               "message": "Shaka Error NETWORK.TIMEOUT (https://cdn.example/seg.m4f,1)"}
    flat = mod.flatten_row(_row("t", 1003, timeout))
    assert flat["shaka_error_name"] == "NETWORK.TIMEOUT" and flat["shaka_url_host"] == "cdn.example"
    assert flat["nested_error_name"] == "" and flat["flow_context"] == "" and flat["shaka_version"] == ""


def test_flatten_rows_dedupes_on_messageid():
    rows = [_row("a", 3016, SHAKA_3016), _row("a", 3016, SHAKA_3016), _row("c", 3016, SHAKA_3016)]
    assert [r["messageid"] for r in mod.flatten_rows(rows)] == ["a", "c"]


def test_text_only_errordescription_kept():
    row = _row("a", 3016, SHAKA_3016)
    payload = json.loads(row["eventdata"])
    payload["errordescription"] = "E8 : plain text"
    row["eventdata"] = json.dumps(payload)
    assert mod.flatten_row(row)["error_text"] == "E8 : plain text"


def test_invalid_json_raises():
    bad = _row("a", 3016, SHAKA_3016)
    bad["eventdata"] = "{not json"
    with pytest.raises(ValueError):
        mod.flatten_rows([bad])


def test_missing_columns_raises():
    with pytest.raises(ValueError):
        mod.flatten_rows([{"messageid": "a"}])
