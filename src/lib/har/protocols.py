"""Protocol skeletons for shared HAR entry loading."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class HarEntry:
    """Normalized HAR log entry."""

    url: str
    method: str
    status: int
    started_datetime: str


@runtime_checkable
class HarEntryLoader(Protocol):
    """SRP seam seeded from vod-asset-ingestion-mapping's loader.

    The shared loader boundary replaces:
    - github_copilot/applauseInvestigation/scripts/analyze_har.py::iter_entries()
    - github_copilot/vod-playback-timing-probe/scripts/extract_content_ids_from_har.py::_load_entries()
    - github_copilot/vod-playback-timing-probe/scripts/summarize_har_playbacks.py::_load_entries()
    - github_copilot/vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()
    """

    def load_entries(self, har_path: Path) -> list[HarEntry]:
        ...
