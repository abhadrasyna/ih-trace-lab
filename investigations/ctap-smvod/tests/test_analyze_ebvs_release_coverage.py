"""Tests for analyze_ebvs_release_coverage.py (offline)."""
from __future__ import annotations

from datetime import date

import pytest
from conftest import load_script

mod = load_script("analyze_ebvs_release_coverage.py")


def _rows():
    return [
        {"sessionId": "e1", "playback_outcome": "EBVS"}, {"sessionId": "e2", "playback_outcome": "EBVS"},
        {"sessionId": "e3", "playback_outcome": "EBVS"}, {"sessionId": "d1", "playback_outcome": "DESTROY"},
        {"sessionId": "e1", "playback_outcome": "EBVS"}, {"sessionId": " ", "playback_outcome": "EBVS"},
    ]


def test_classify_dedupes_and_flags_setup_and_release():
    detail = mod.classify(_rows(), {"e1", "e2", "d1"}, {"e1", "d1"})
    flags = {r["sessionId"]: (r["has_setup"], r["has_release"]) for r in detail}
    assert flags == {"d1": ("true", "true"), "e1": ("true", "true"), "e2": ("true", "false"), "e3": ("false", "false")}


def test_classify_rejects_conflicting_outcomes():
    with pytest.raises(ValueError, match="two playback outcomes"):
        mod.classify([{"sessionId": "a", "playback_outcome": "EBVS"}, {"sessionId": "a", "playback_outcome": "DESTROY"}], set(), set())


def test_summarize_takes_missing_pct_over_sessions_with_setup():
    summary = {r["playback_outcome"]: r for r in mod.summarize(mod.classify(_rows(), {"e1", "e2", "d1"}, {"e1", "d1"}))}
    assert summary["EBVS"] == {"playback_outcome": "EBVS", "sessions": "3", "with_setup": "2", "with_release": "1",
                               "setup_without_release": "1", "release_missing_pct": "50.0"}
    assert summary["DESTROY"]["release_missing_pct"] == "0.0"


def test_summarize_leaves_pct_blank_when_no_setup_seen():
    (row,) = mod.summarize(mod.classify([{"sessionId": "x", "playback_outcome": ""}], set(), set()))
    assert row["playback_outcome"] == "(blank)" and row["release_missing_pct"] == ""


def test_load_release_ids_reads_next_day_when_present(tmp_path):
    (tmp_path / "2026-10-30_smvod-release.csv").write_text("sessionId\na\n", encoding="utf-8")
    ids, paths = mod.load_release_ids(tmp_path, date(2026, 10, 30))
    assert ids == {"a"} and len(paths) == 1
    (tmp_path / "2026-10-31_smvod-release.csv").write_text("sessionId\nb\n", encoding="utf-8")
    ids, paths = mod.load_release_ids(tmp_path, date(2026, 10, 30))
    assert ids == {"a", "b"} and len(paths) == 2


def test_load_release_ids_requires_the_day_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        mod.load_release_ids(tmp_path, date(2026, 10, 30))
