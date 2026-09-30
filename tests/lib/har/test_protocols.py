"""Tests for src.lib.har.protocols."""
from __future__ import annotations

from pathlib import Path

from src.lib.har.protocols import HarEntry, HarEntryLoader


class _ConformingHarEntryLoader:
    def load_entries(self, har_path: Path) -> list[HarEntry]:
        return [
            HarEntry(
                url="https://example.test/manifest.mpd",
                method="GET",
                status=200,
                started_datetime="2026-09-30T00:00:00Z",
            )
        ]


class _MissingLoaderMethod:
    pass


def test_conforming_stub_satisfies_har_entry_loader_protocol() -> None:
    assert isinstance(_ConformingHarEntryLoader(), HarEntryLoader)


def test_non_conforming_stub_does_not_satisfy_protocol() -> None:
    assert not isinstance(_MissingLoaderMethod(), HarEntryLoader)
