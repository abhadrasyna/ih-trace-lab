"""Fetch missing daily extracts through an injected ``AthenaClient`` and save them locally.

Dates are fetched serially: the blocking client already runs one query at a time, so there is no
concurrent FCID propagation to carry.
"""
from __future__ import annotations

import csv
import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.lib.local_data import daily_filename
from src.lib.athena.protocols import AthenaClient
from src.lib.csv_io.csv_file import CsvFileWriter
from src.lib.logging.redact import redact_params

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.lib.athena_fetch")
QUERY_DIR = Path(__file__).resolve().parents[4] / "queries" / "athena"
PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
SUCCEEDED = "SUCCEEDED"


class FetchError(Exception):
    """Raised when a registered query cannot be rendered, run or saved."""


@dataclass(frozen=True)
class FetchResult:
    saved: dict[date, Path]
    skipped: list[date]  # already saved locally
    empty: list[date]  # query returned no rows and no fieldnames were given, so nothing was saved


def render_query(query_name: str, params: Mapping[str, str], query_dir: Path = QUERY_DIR) -> str:
    path = query_dir / f"{query_name}.sql"
    if not path.is_file():
        raise FetchError(f"query is not registered under queries/athena/: {query_name}")
    sql = path.read_text(encoding="utf-8")
    placeholders = set(PLACEHOLDER_RE.findall(sql))
    if "date" not in placeholders:
        raise FetchError(f"query {query_name} has no {{{{date}}}} placeholder; it cannot be fetched per date")
    for key, value in params.items():
        if "'" in str(value):
            raise FetchError(f"query parameter {key} must not contain a quote")
    missing = sorted(placeholders - set(params))
    if missing:
        raise FetchError(f"missing query parameters for {query_name}: {', '.join(missing)}")
    return PLACEHOLDER_RE.sub(lambda match: str(params[match.group(1)]), sql)


def _run_one(client: AthenaClient, query_name: str, sql: str) -> list[dict[str, str]]:
    try:
        execution_id = client.start_query(sql, {})
        state = client.poll_status(execution_id)
        if state != SUCCEEDED:
            raise FetchError(f"{query_name} ended in state {state}")
        return client.fetch_results(execution_id).rows
    except FetchError:
        raise
    except Exception as exc:  # boundary: no client/boto3 exception type leaks to callers
        raise FetchError(f"{query_name} failed: {exc}") from exc


def _save(path: Path, rows: list[dict[str, str]], fieldnames: Sequence[str] | None) -> bool:
    columns = list(fieldnames) if fieldnames else (list(rows[0]) if rows else [])
    if not columns:
        return False
    temp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        CsvFileWriter().write_rows(str(temp), rows, columns)
        os.replace(temp, path)  # a failed write never leaves a partial file under the final name
    except (OSError, ValueError, csv.Error) as exc:
        temp.unlink(missing_ok=True)
        raise FetchError(f"cannot save {path}: {exc}") from exc
    return True


def fetch_missing(
    client: AthenaClient,
    query_name: str,
    dates: Sequence[date],
    *,
    artifact: str,
    out_dir: Path,
    params: Mapping[str, str] | None = None,
    fieldnames: Sequence[str] | None = None,
    query_dir: Path = QUERY_DIR,
) -> FetchResult:
    """Run ``query_name`` once per date that has no saved ``<date>_<artifact>.csv`` in ``out_dir``."""
    base = dict(params or {})
    saved: dict[date, Path] = {}
    skipped: list[date] = []
    empty: list[date] = []
    for day in dates:
        path = out_dir / daily_filename(day, artifact)
        if path.is_file() and path.stat().st_size > 0:
            skipped.append(day)
            continue
        sql = render_query(query_name, {**base, "date": day.isoformat()}, query_dir)
        LOGGER.debug("Athena fetch start query=%s date=%s params=%s", query_name, day,
                     redact_params({**base, "date": day.isoformat()}, {"date"}))
        started = time.perf_counter()
        try:
            rows = _run_one(client, query_name, sql)
        except FetchError as exc:
            LOGGER.error("Athena fetch failed query=%s date=%s: %s", query_name, day, exc)
            raise
        if not _save(path, rows, fieldnames):
            empty.append(day)
            continue
        saved[day] = path
        LOGGER.info("Athena fetch saved query=%s date=%s rows=%d duration_ms=%d", query_name, day,
                    len(rows), int((time.perf_counter() - started) * 1000))
    return FetchResult(saved=saved, skipped=skipped, empty=empty)
