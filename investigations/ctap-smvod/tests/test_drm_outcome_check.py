from __future__ import annotations

import pytest
from lib.drm_funnel import SOURCE_DRM_ONLY, SOURCE_MERGE, ClassifiedSession

from lib import drm_outcome_check as mod


def _cs(sid: str, source: str = SOURCE_MERGE, lic: str = "no_request", code: str = "") -> ClassifiedSession:
    return ClassifiedSession(sid, source, "vod", "no_drm_activity", lic, code)


def test_tabulates_only_the_requested_cell_by_playback_outcome() -> None:
    sessions = [
        _cs("a"), _cs("b"), _cs("c"), _cs("d", code="1001"), _cs("e", lic="success"),
    ]
    outcomes = {"a": "EBVS", "b": "EBVS", "c": "DESTROY", "d": "EBVS", "e": "EBVS"}
    assert mod.tabulate_playback_outcome(sessions, outcomes, "no_request") == {"EBVS": 2, "DESTROY": 1}
    assert mod.tabulate_playback_outcome(sessions, outcomes, "no_request", "1001") == {"EBVS": 1}


def test_outcome_map_joins_several_columns_and_labels_blanks() -> None:
    rows = [{"sessionId": "a", "playback_outcome": "", "outcome_match_status": "no_match"},
            {"sessionId": "b", "playback_outcome": "EBVS", "outcome_match_status": ""}]
    got = mod.outcome_map(rows, ["playback_outcome", "outcome_match_status"])
    assert got == {"a": "(blank) | no_match", "b": "EBVS | (blank)"}


def test_outcome_map_merges_duplicates_and_rejects_conflicts() -> None:
    rows = [{"sessionId": "a", "playback_outcome": ""}, {"sessionId": "a", "playback_outcome": "EBVS"},
            {"sessionId": "a", "playback_outcome": ""}, {"sessionId": "b", "playback_outcome": "DESTROY"}]
    assert mod.outcome_map(rows) == {"a": "EBVS", "b": "DESTROY"}
    with pytest.raises(ValueError, match="conflicting"):
        mod.outcome_map(rows + [{"sessionId": "b", "playback_outcome": "EBVS"}])


def test_drm_only_and_blank_outcomes_are_labelled_not_guessed() -> None:
    sessions = [_cs("a", SOURCE_DRM_ONLY), _cs("b"), _cs("c")]
    result = mod.tabulate_playback_outcome(sessions, {}, "no_request")
    assert result == {mod.NO_MERGE_OUTCOME: 1, mod.BLANK_OUTCOME: 2}


def test_sample_session_ids_filters_cell_and_group_and_limits() -> None:
    sessions = [_cs("c"), _cs("a"), _cs("b"), _cs("x", lic="success"), _cs("e", code="1001")]
    outcomes = {"a": "EBVS", "b": "missing", "c": "missing"}
    got = mod.sample_session_ids(sessions, outcomes, "no_request", group_prefix="missing", limit=1)
    assert got == ["b"]
    assert mod.sample_session_ids(sessions, outcomes, "no_request", group_prefix="nothing") == []
    with pytest.raises(ValueError, match="limit"):
        mod.sample_session_ids(sessions, outcomes, "no_request", limit=-3)
