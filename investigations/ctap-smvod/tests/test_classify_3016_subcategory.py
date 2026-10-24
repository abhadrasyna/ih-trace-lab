from __future__ import annotations

from conftest import load_script

mod = load_script("classify_3016_subcategory.py")


def _row(code="3016", status="", met="") -> dict:
    return {"errorcode": code, "pipeline_status": status, "media_error_type": met}


def test_each_known_status_maps_to_expected_subcategory() -> None:
    cases = [
        (_row("3014"), mod.MSE_APPEND, "P3"),
        (_row("3015", "PipelineStatus::Decode error"), mod.MSE_APPEND, "P3"),
        (_row(status="PipelineStatus::Video decoder reinitialization failed"), mod.REINIT, "P2"),
        (_row(status="Video decoder reinitialization failed"), mod.REINIT, "P2"),
        (_row(met="4"), mod.NO_DATA, "P2"),
        (_row(status="PipelineStatus::Audio renderer error"), mod.AUDIO, "P3"),
        (_row(status="Pipeline disconnected"), mod.AUDIO, "P3"),
        (_row(status="PipelineStatus::Media failed to decode"), mod.VIDEO_DECODE, "P1"),
        (_row(status="Media failed to decode"), mod.VIDEO_DECODE, "P1"),
    ]
    for row, sub, prio in cases:
        assert mod.classify(row) == sub, row
        assert mod.PRIORITY[sub] == prio


def test_unknown_status_is_uncategorised_not_dropped() -> None:
    assert mod.classify(_row(status="something new")) == mod.UNCATEGORISED
    assert mod.classify({}) == mod.UNCATEGORISED
    assert mod.PRIORITY[mod.UNCATEGORISED] == "P?"
