"""On-disk store for per-window Lightstep parts: one JSON part file plus a manifest, both written atomically.

A part holds the raw fetched series (points included), so stitching is exact and ``smvod-ts`` can be derived
after stitching. The manifest is written after the part file; a part is reused only when both exist and agree
on window, kind, query fingerprint, series count and sha256. Pure file I/O; no network.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger("scripts.lib.lightstep_parts")
Series = dict[str, object]
Window = tuple[datetime, datetime]


def query_fingerprint(**parts: object) -> str:
    """Stable sha256 over everything that determines a part's content (query text, project, region, window, ...)."""
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


@dataclass(frozen=True)
class PartStore:
    """Parts of one tenant and day under ``directory`` (created on first save)."""

    directory: Path

    def _part_path(self, kind: str, index: int) -> Path:
        return self.directory / f"{kind}_{index:02d}.json"

    def _manifest_path(self, kind: str, index: int) -> Path:
        return self.directory / f"{kind}_{index:02d}.manifest.json"

    def save(self, kind: str, index: int, window: Window, fingerprint: str, series: list[Series]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        body = json.dumps(series, separators=(",", ":")).encode("utf-8")
        _atomic_write(self._part_path(kind, index), body)
        manifest = {
            "kind": kind, "index": index, "window": [window[0].isoformat(), window[1].isoformat()],
            "fingerprint": fingerprint, "series_count": len(series), "sha256": hashlib.sha256(body).hexdigest(),
        }
        _atomic_write(self._manifest_path(kind, index), json.dumps(manifest, indent=2).encode("utf-8"))

    def load(self, kind: str, index: int, window: Window, fingerprint: str) -> list[Series] | None:
        """Returns the saved series when the part verifies, else None (the reason is logged)."""
        part, manifest_path = self._part_path(kind, index), self._manifest_path(kind, index)
        if not part.exists() and not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            body = part.read_bytes()
            problem = self._mismatch(manifest, body, kind, window, fingerprint)
            series = None if problem else json.loads(body)
            if series is not None and len(series) != manifest["series_count"]:
                problem = "series count differs from the manifest"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            problem = f"{type(exc).__name__}: {exc}"
        if problem:
            LOGGER.warning("part %s_%02d not reusable, will refetch: %s", kind, index, problem)
            return None
        return series

    @staticmethod
    def _mismatch(manifest: dict[str, object], body: bytes, kind: str, window: Window, fingerprint: str) -> str | None:
        if manifest["kind"] != kind or manifest["window"] != [window[0].isoformat(), window[1].isoformat()]:
            return "kind or window differs from the manifest"
        if manifest["fingerprint"] != fingerprint:
            return "query fingerprint changed"
        if manifest["sha256"] != hashlib.sha256(body).hexdigest():
            return "sha256 does not match the manifest"
        return None

    def discard(self) -> None:
        """Deletes this store's folder (only ever ``<TENANT>_<date>/``); a missing folder is fine."""
        shutil.rmtree(self.directory, ignore_errors=True)
