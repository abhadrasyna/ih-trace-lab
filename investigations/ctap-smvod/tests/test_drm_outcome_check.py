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


def test_outcome_map_merges_duplicates_and_rejects_conflicts() -> None:
    rows = [{"sessionId": "a", "playback_outcome": ""}, {"sessionId": "a", "playback_outcome": "EBVS"},
            {"sessionId": "a", "playback_outcome": ""}, {"sessionId": "b", "playback_outcome": "DESTROY"}]
    assert mod.outcome_map(rows) == {"a": "EBVS", "b": "DESTROY"}
    with pytest.raises(ValueError, match="conflicting"):
        mod.outcome_map(rows + [{"sessionId": "b", "playback_outcome": "EBVS"}])


def test_drm_only_and_blank_outcomes_are_labelled_not_guessed() -> None:
    sessions = [_cs("a", SOURCE_DRM_ONLY), _cs("b"), _cs("c")]
    result = mod.tabulate_playback_outcome(sessions, {"b": "  "}, "no_request")
    assert result == {mod.NO_MERGE_OUTCOME: 1, mod.BLANK_OUTCOME: 2}
