"""Concrete `HarEntryLoader` implementing `functional-code-taxonomy` FCT-2's `Protocol`.

See `docs/plan/src-lib-migration/har-lib-migration/stories.md` HLM-2 for the full spec this implements.

`PYTHON_DESIGN.md` trigger: SRP — the same ~5-line "load HAR `log.entries`" loader was reimplemented four times
across `github_copilot` (`applauseInvestigation/scripts/analyze_har.py::iter_entries()`,
`vod-playback-timing-probe/scripts/extract_content_ids_from_har.py::_load_entries()` and
`summarize_har_playbacks.py::_load_entries()` (twice in the same project), and
`vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()`). This module replaces all four with
one mechanism. Per HLM-1's resolution, `load_json_entries()`'s JSON-mimetype/URL filtering and response-body
parsing is explicitly out of scope — that stays project-specific business logic for a future consumer, not a gap
here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import IO

from .exceptions import HarFormatError
from .protocols import HarEntry


class JsonHarEntryLoader:
    """Loads a HAR document's `log.entries` into a list of normalized `HarEntry` records.

    Named `JsonHarEntryLoader`, not `HarEntryLoader`, because `protocols.py`'s `HarEntryLoader` is already the
    `Protocol` name itself (stale naming in this story's `stories.md` diagram calls the Protocol `HarLoaderProtocol`
    — corrected here to match the actual landed `functional-code-taxonomy` FCT-2 shape).
    """

    def load_entries(self, har_path: str | Path | IO[str] | IO[bytes]) -> list[HarEntry]:
        """Reads `har_path` (a file path or an already-open file handle) and returns its `log.entries`.

        Raises `HarFormatError` for invalid JSON, invalid UTF-8, a missing/non-dict `log`, a missing/non-list
        `log.entries`, or any entry whose `request.url`/`request.method`/`response.status` is missing or the
        wrong type — never a bare `KeyError`/`TypeError`/`ValueError`/`UnicodeDecodeError`/`json.JSONDecodeError`.
        """
        raw_text = self._read_text(har_path)
        try:
            document = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise HarFormatError(f"HAR document is not valid JSON: {exc}") from exc

        log = document.get("log") if isinstance(document, dict) else None
        if not isinstance(log, dict):
            raise HarFormatError("HAR document is missing a dict-valued top-level 'log' key")

        entries = log.get("entries")
        if not isinstance(entries, list):
            raise HarFormatError("HAR document's 'log' is missing a list-valued 'entries' key")

        return [self._to_har_entry(entry, index) for index, entry in enumerate(entries)]

    @staticmethod
    def _read_text(har_path: str | Path | IO[str] | IO[bytes]) -> str:
        try:
            if isinstance(har_path, (str, Path)):
                return Path(har_path).read_text(encoding="utf-8-sig")
            content = har_path.read()
            text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
            return text.removeprefix("\ufeff")
        except UnicodeDecodeError as exc:
            raise HarFormatError(f"HAR document is not valid UTF-8: {exc}") from exc

    @staticmethod
    def _to_har_entry(entry: object, index: int) -> HarEntry:
        if not isinstance(entry, dict):
            raise HarFormatError(f"HAR entry at index {index} is not a JSON object")
        request = entry.get("request")
        response = entry.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
            raise HarFormatError(f"HAR entry at index {index} is missing a 'request'/'response' object")
        url = request.get("url")
        method = request.get("method")
        status = response.get("status")
        if not isinstance(url, str):
            raise HarFormatError(f"HAR entry at index {index} has a missing/non-string 'request.url'")
        if not isinstance(method, str):
            raise HarFormatError(f"HAR entry at index {index} has a missing/non-string 'request.method'")
        if not isinstance(status, int) or isinstance(status, bool):
            raise HarFormatError(f"HAR entry at index {index} has a missing/non-integer 'response.status'")
        started_datetime = entry.get("startedDateTime", "")
        if not isinstance(started_datetime, str):
            raise HarFormatError(f"HAR entry at index {index} has a non-string 'startedDateTime'")
        return HarEntry(
            url=url,
            method=method,
            status=status,
            started_datetime=started_datetime,
        )
