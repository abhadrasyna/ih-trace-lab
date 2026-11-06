"""Offline tests for the shared src/lib helpers promoted in SU-2."""
from __future__ import annotations

import pytest

from src.lib.playback import is_success
from src.lib.ranking import rank_by_count
from src.lib.user_agent import is_webview, parse_user_agent

P11_UA = ("Mozilla/5.0 (Linux; Android 13; P11 Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Version/4.0 Chrome/156.0.8078.47 Mobile Safari/537.36")


def test_parses_p11_webview_ua():
    parsed = parse_user_agent(P11_UA)
    assert parsed["device_model"] == "P11"
    assert parsed["build_id"] == "TP1A.220624.014"
    assert (parsed["os_name"], parsed["os_version"]) == ("Android", "13")
    assert parsed["chrome_version"] == "156.0.8078.47"
    assert parsed["is_webview"] is True and is_webview(P11_UA)
    assert parsed["ua_shape"] == "android_build"


def test_non_wv_and_reduced_ua():
    plain = parse_user_agent(P11_UA.replace("; wv)", ")"))
    assert plain["is_webview"] is False
    reduced = parse_user_agent("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36")
    assert reduced["ua_shape"] == "android_reduced"
    assert parse_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")["ua_shape"] == "desktop"
    assert parse_user_agent("")["ua_shape"] == "unparsed"
    assert parse_user_agent("curl/8.0")["ua_shape"] == "unparsed"


def test_success_means_destroy_only():
    assert is_success("DESTROY") and is_success(" DESTROY ")
    for outcome in ("EBVS", "INCOMPLETE_NO_DESTROY", "", None):
        assert not is_success(outcome)


def test_rank_by_count_stable_ties():
    rows = [{"hh": h} for h in ("b", "a", "c", "c", "b", "d")]
    ranked = rank_by_count(rows, "hh", top=3)
    assert [(r["key"], r["count"]) for r in ranked] == [("b", 2), ("c", 2), ("a", 1)]  # first-seen order on ties
    by_name = rank_by_count(rows, "hh", tie_breakers=[lambda k: k])
    assert [r["key"] for r in by_name] == ["b", "c", "a", "d"]
    assert [r["rank"] for r in by_name] == [1, 2, 3, 4]
    with pytest.raises(ValueError):
        rank_by_count([{"hh": None}], "hh")
