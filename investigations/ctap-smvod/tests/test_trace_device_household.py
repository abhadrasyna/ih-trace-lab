"""Tests for trace_device_household.py."""
from __future__ import annotations

import pytest

from conftest import load_script

mod = load_script("trace_device_household.py")


def _s(sid, content, outcome="FAILED"):
    return {"householdId": "h1", "deviceId": "d1", "sessionId": sid, "content": content,
            "span_name": "SetupSession", "playback_outcome": outcome}


def _e(sid, code):
    return {"householdId": "h1", "deviceId": "d1", "sessionId": sid, "errorcode": code,
            "shaka_category": "3", "shaka_error_name": "MEDIA.VIDEO_ERROR", "pipeline_status": "DECODE"}


def test_summarize_joins_errors_to_content():
    s = mod.summarize([_s("s1", "A"), _s("s2", "A", "OK")], [_e("s1", "3016"), _e("s1", "3016")])
    assert s["playback_sessions"] == 2
    assert s["attempts_by_content"]["A"] == 2
    assert s["errors_by_content"]["A"]["3016"] == 2
    assert s["households"] == ["h1"]


def test_filter_rows_missing_column_raises():
    with pytest.raises(ValueError):
        mod.filter_rows([{"x": "1"}], "d1")


def test_blank_content_row_does_not_overwrite_and_blank_sid_skipped():
    s = mod.summarize([_s("s1", "A"), _s("s1", ""), _s("", "B")], [_e("", "3016")])
    assert s["attempts_by_content"] == {"A": 1}
    assert s["playback_sessions"] == 1 and s["error_sessions"] == 0
    assert s["errors_by_content"]["(no session match)"]["3016"] == 1


def test_conflicting_content_raises():
    with pytest.raises(ValueError):
        mod.session_content_map([_s("s1", "A"), _s("s1", "B")])
