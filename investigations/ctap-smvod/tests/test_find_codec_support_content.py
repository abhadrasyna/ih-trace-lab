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
    assert mod.content_by_session([{"sessionId": "s1", "content": " A "}, {"sessionId": "s2", "content": ""}]) == {"s1": "A"}
