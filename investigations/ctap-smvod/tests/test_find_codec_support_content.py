"""Tests for find_codec_support_content.py."""
from __future__ import annotations

from conftest import load_script

mod = load_script("find_codec_support_content.py")

RAW_TRUE = '{"a":{"audio/mp4":true,"audio/mp4; codecs=\\"ec-3\\"":true,"video/mp2t; codecs=\\"ec-3\\"":true}}'
RAW_FALSE = '{"a":{"audio/mp4; codecs=\\"ec-3\\"":false}}'


def test_supported_mimes_true_vs_false():
    assert mod.supported_mimes(RAW_TRUE, "ec-3") == ["audio/mp4", "video/mp2t"]
    assert mod.supported_mimes(RAW_FALSE, "ec-3") == []
    assert mod.supported_mimes(RAW_FALSE, "ec-3", "false") == ["audio/mp4"]


def test_match_sessions_and_content_join():
    flat = [{"sessionId": "s1", "raw_eventdata": RAW_TRUE}, {"sessionId": "s2", "raw_eventdata": RAW_FALSE}]
    hits = mod.match_sessions(flat, "ec-3", "true")
    assert [h["sessionId"] for h in hits] == ["s1"]
    assert mod.session_info([{"sessionId": "s1", "content": " A ", "position_not_moved": "false"},
                             {"sessionId": "s2", "content": ""}]) == {
        "s1": {"content": "A", "position_not_moved": "false", "playback_outcome": ""}}


def test_probe_state():
    assert mod.probe_state(RAW_TRUE, "ec-3") == "true"
    assert mod.probe_state(RAW_FALSE, "ec-3") == "false"
    assert mod.probe_state('{"a":{}}', "ec-3") == "absent"


def test_split_by_probe_counts_sessions_once_and_position_moved():
    info = {"s1": {"content": "A", "position_not_moved": "false"}, "s2": {"content": "A", "position_not_moved": "true"},
            "s3": {"content": "A", "position_not_moved": ""}}
    flat = [{"errorcode": "6012", "sessionId": "s1", "raw_eventdata": RAW_FALSE},
            {"errorcode": "6012", "sessionId": "s1", "raw_eventdata": RAW_TRUE},
            {"errorcode": "6012", "sessionId": "s2", "raw_eventdata": RAW_FALSE},
            {"errorcode": "6012", "sessionId": "s3", "raw_eventdata": RAW_FALSE},
            {"errorcode": "6012", "sessionId": "s4", "raw_eventdata": '{"a":{}}'}]
    assert mod.split_by_probe(flat, info, "ec-3") == [["6012", "A", "1", "1", "2", "0"]]
