"""Offline tests for the promoted debug-event parser."""
from __future__ import annotations

import json

from src.lib.debug_events import extract_error_app_version, extract_error_client_flags, flatten_row, split_clientid


def test_flatten_player_error_and_app_version():
    data = {"sessionid": "s1", "errorcode": 6001,
            "errordescription": {"errordescription": "E86001", "app_version": "v1", "user_agent": "UA",
                                 "shakaerror": {"code": 6001, "message": "m"}}}
    row = {"datetime": "t", "clientid": "dev:hh", "eventclass": "PLAYER", "eventid": "PLAYER_ERROR",
           "eventdata": json.dumps(data)}
    flat = flatten_row(row)
    assert (flat["device_id"], flat["household_id"], flat["shaka_code"], flat["user_agent"]) == ("dev", "hh", 6001, "UA")
    assert extract_error_app_version(data) == "v1"


def test_malformed_input_is_tolerated():
    assert split_clientid("nocolon") == (None, None)
    assert extract_error_app_version({"errordescription": "plain text"}) is None
    assert flatten_row({"eventid": "PLAYER_ERROR", "eventdata": "{bad"})["session_id"] is None


def test_error_client_flags_nested_booleans():
    data = {"errordescription": {"drmsupported": False, "iswebview": True}}
    assert extract_error_client_flags(data) == {"drmsupported": False, "iswebview": True}


def test_error_client_flags_absent_or_non_boolean_is_none():
    none = {"drmsupported": None, "iswebview": None}
    assert extract_error_client_flags({"errordescription": "plain text"}) == none
    assert extract_error_client_flags({"errordescription": {"drmsupported": "false"}}) == none
    assert extract_error_client_flags({"drmsupported": True}) == none
