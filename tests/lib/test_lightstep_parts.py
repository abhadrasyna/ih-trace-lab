"""Offline tests for scripts/lib/lightstep_parts.py."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.lightstep_parts import PartStore, query_fingerprint

WINDOW = (datetime(2026, 10, 29, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 1, tzinfo=timezone.utc))
SERIES = [{"group-labels": ["a=1"], "points": [[1, 2]]}]


def _store(tmp_path: Path) -> PartStore:
    store = PartStore(tmp_path / "ZA_2026-10-29")
    store.save("ctap", 1, WINDOW, "fp", SERIES)
    return store


def test_round_trip_and_empty_part(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.load("ctap", 1, WINDOW, "fp") == SERIES
    store.save("ctap", 2, WINDOW, "fp", [])
    assert store.load("ctap", 2, WINDOW, "fp") == []


def test_missing_part_is_none(tmp_path: Path) -> None:
    assert PartStore(tmp_path / "none").load("ctap", 1, WINDOW, "fp") is None


def test_changed_fingerprint_window_or_content_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.load("ctap", 1, WINDOW, "other") is None
    assert store.load("ctap", 1, (WINDOW[0], WINDOW[0]), "fp") is None
    (store.directory / "ctap_01.json").write_text("[]", encoding="utf-8")
    assert store.load("ctap", 1, WINDOW, "fp") is None


def test_part_without_manifest_or_truncated_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    (store.directory / "ctap_01.manifest.json").unlink()
    assert store.load("ctap", 1, WINDOW, "fp") is None
    store.save("ctap", 1, WINDOW, "fp", SERIES)
    (store.directory / "ctap_01.json").write_bytes(b'[{"group-la')
    assert store.load("ctap", 1, WINDOW, "fp") is None


def test_discard_removes_only_its_folder_and_fingerprint_is_stable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    sibling = tmp_path / "keep.txt"
    sibling.write_text("x", encoding="utf-8")
    store.discard()
    store.discard()
    assert not store.directory.exists() and sibling.exists()
    assert query_fingerprint(a=1, b="x") == query_fingerprint(b="x", a=1) != query_fingerprint(a=2, b="x")
