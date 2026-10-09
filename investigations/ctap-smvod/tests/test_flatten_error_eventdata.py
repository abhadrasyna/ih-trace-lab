"""Tests for flatten_error_eventdata.py."""
from __future__ import annotations

import json

import pytest

from conftest import load_script

mod = load_script("flatten_error_eventdata.py")

SHAKA_3016 = {"severity": 2, "category": 3, "code": 3016, "data": [3, None, "PipelineStatus::PIPELINE_ERROR_DECODE"],
              "message": "Shaka Error MEDIA.VIDEO_ERROR"}
INNER_BODY = json.dumps({"title": "Not Authorized", "status": 403,
                         "detail": 'MDRM server returned 400, body: "{\\"code\\":\\"6211\\",\\"message\\":\\"x\\"}"'})
SHAKA_6007 = {"code": 6007, "category": 6, "message": "m", "data": [
    {"code": 1001, "data": ["https://lic.example/widevine/x", 403, INNER_BODY, {}, 2, "https://lic.example/widevine/x"]}]}


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
