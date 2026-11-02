"""Tests for analyze_release_gap_webview.py (offline)."""
from __future__ import annotations

from conftest import load_script

mod = load_script("analyze_release_gap_webview.py")


def _cov(sid, outcome, setup, release):
    return {"sessionId": sid, "playback_outcome": outcome, "has_setup": setup, "has_release": release}


def test_only_setup_without_release_sessions_are_judged_and_unknown_is_not_non_wv():
    coverage = [_cov("a", "EBVS", "true", "false"), _cov("b", "EBVS", "true", "false"), _cov("c", "EBVS", "true", "true"),
                _cov("d", "EBVS", "false", "false"), _cov("e", "DESTROY", "true", "false")]
    setup = [{"sessionId": "a", "raw_user_agent": "Mozilla; wv)", "Platform": ""}, {"sessionId": "b", "raw_user_agent": "Chrome", "Platform": ""},
             {"sessionId": "e", "raw_user_agent": "", "Platform": ""}]
    detail = {r["sessionId"]: r["is_wv"] for r in mod.release_gap_webview(coverage, setup)}
    assert detail == {"a": "true", "b": "false", "e": ""}


def test_summarize_pct_over_known_and_total_row():
    detail = [{"sessionId": "a", "playback_outcome": "EBVS", "is_wv": "true"}, {"sessionId": "b", "playback_outcome": "EBVS", "is_wv": ""},
              {"sessionId": "c", "playback_outcome": "DESTROY", "is_wv": ""}]
    rows = {r["playback_outcome"]: r for r in mod.summarize(detail)}
    assert rows["EBVS"]["wv_pct_of_known"] == "100.0" and rows["EBVS"]["unknown"] == "1"
    assert rows["DESTROY"]["wv_pct_of_known"] == "" and rows["TOTAL"]["gap_sessions"] == "3"
