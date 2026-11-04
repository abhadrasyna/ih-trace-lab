"""Lightstep-side data for the usage report: sm-vod SetupSession requests and trace ids per session.

Two implementers of `RequestSource` serve one tenant each: `LocalExportSource` (default, reads `<date>_smvod.csv`) and `LiveLightstepSource` (`--live-lightstep`, takes an injected query runner).
The CLI picks one; neither falls back to the other. The export has no status code, so there is no 5xx count.
"""
from __future__ import annotations

import csv
import logging
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from src.lib.logging.redact import redact_params

from .errors import LightstepSourceError
from .roster import Household

LOGGER = logging.getLogger(__name__)

QUERY_FILE = Path(__file__).resolve().parents[3] / "queries" / "lightstep" / "usage-tracking-smvod-by-device.md"
DEFAULT_EXPORT_ROOT = Path(__file__).resolve().parents[3] / "investigations" / "ctap-smvod" / "data" / "lightstep"
_SAFE_VALUE = re.compile(r"[A-Za-z0-9_\-:.]+")
_LOG_ALLOW = {"tenant", "date"}

# Takes the final UQL and the report day (the runner sets the UTC-day window) and returns Lightstep series dicts (`group-labels`, `points`).
QueryRunner = Callable[[str, date], list[dict[str, object]]]


@dataclass(frozen=True)
class RequestRow:
    session_id: str
    household_id: str
    device_id: str
    trace_id: str
    request_count: int


class RequestSource(Protocol):
    def fetch_requests(self, households: Sequence[Household], day: date) -> list[RequestRow]: ...


def request_counts(rows: Iterable[RequestRow], households: Sequence[Household]) -> dict[tuple[str, str], int]:
    """Request count per roster `(hhid, device_id)`; a pair with no rows is 0, which is activity data, not an error."""
    totals: Counter[tuple[str, str]] = Counter()
    for row in rows:
        totals[(row.household_id, row.device_id)] += row.request_count
    return {(h.hhid, m.device_id): totals[(h.hhid, m.device_id)] for h in households for m in h.members}


def _pairs(households: Sequence[Household]) -> set[tuple[str, str]]:
    return {(h.hhid, m.device_id) for h in households for m in h.members}


def _check_tenant(tenant: str, households: Iterable[Household]) -> None:
    for household in households:
        if household.tenant != tenant:
            raise LightstepSourceError(f"household {household.hhid} is tenant {household.tenant}, source is {tenant}")


class LocalExportSource:
    """Reads the tenant-wide `<date>_smvod.csv` under `<root>/<TENANT>/` and keeps only roster pairs."""

    def __init__(self, tenant: str, root: Path = DEFAULT_EXPORT_ROOT) -> None:
        self._tenant = tenant
        self._dir = root / tenant

    def fetch_requests(self, households: Sequence[Household], day: date) -> list[RequestRow]:
        _check_tenant(self._tenant, households)
        pairs = _pairs(households)
        rows = _mapped(_row_from_export, self._read_csv(f"{day}_smvod.csv"))
        return [r for r in rows if (r.household_id, r.device_id) in pairs]

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        path = self._dir / name
        if not path.is_file():
            raise LightstepSourceError(f"local export missing: {path}")
        try:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                return list(csv.DictReader(handle))
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            raise LightstepSourceError(f"cannot read {path}: {exc}") from exc


def _row_from_export(r: dict[str, str]) -> RequestRow:
    return RequestRow(r["sessionId"], r["householdId"], r["deviceId"], r["lightstep.trace_id"], _count(r["sum"]))


class LiveLightstepSource:
    """Queries Lightstep for the roster pairs only, through an injected runner that takes the final UQL."""

    def __init__(self, tenant: str, run_query: QueryRunner, tenant_filter: str = "", query_file: Path = QUERY_FILE) -> None:
        self._tenant = tenant
        self._run = run_query
        self._tenant_filter = tenant_filter
        self._query_file = query_file

    def fetch_requests(self, households: Sequence[Household], day: date) -> list[RequestRow]:
        _check_tenant(self._tenant, households)
        pairs = sorted(_pairs(households))
        if not pairs:
            return []
        uql = self._build_uql(pairs)
        shown = redact_params({"tenant": self._tenant, "date": str(day)}, _LOG_ALLOW)
        LOGGER.debug("Lightstep call start", extra={"call_name": "usage.lightstep", "params": shown})
        started = time.monotonic()
        try:
            series = self._run(uql, day)
        except LightstepSourceError:
            raise
        except Exception as exc:
            raise LightstepSourceError(f"Lightstep query failed: {exc}") from exc
        wanted = set(pairs)
        rows = [r for r in _mapped(_row_from_series, series) if (r.household_id, r.device_id) in wanted]
        LOGGER.info(
            "Lightstep call ok",
            extra={"call_name": "usage.lightstep", "params": shown, "row_count": len(rows), "duration_ms": int((time.monotonic() - started) * 1000)},
        )
        return rows

    def _build_uql(self, pairs: Sequence[tuple[str, str]]) -> str:
        clause = " || ".join(f'(householdId == "{_safe(h)}" && deviceId == "{_safe(d)}")' for h, d in pairs)
        template = _query_block(self._query_file)
        if "{{pairs_filter}}" not in template:
            raise LightstepSourceError(f"{self._query_file} has no {{{{pairs_filter}}}} placeholder; refusing a tenant-wide query")
        if self._tenant_filter and "{{tenant_filter}}" not in template:
            raise LightstepSourceError(f"{self._query_file} has no {{{{tenant_filter}}}} placeholder; refusing to drop the shared-project scope")
        return template.replace("{{tenant_filter}}", self._tenant_filter).replace("{{pairs_filter}}", clause)


def _query_block(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LightstepSourceError(f"cannot read query file {path}: {exc}") from exc
    match = re.search(r"^```[^\n]*\n(.*?)\n^```\s*$", text, re.DOTALL | re.MULTILINE)
    if not match:
        raise LightstepSourceError(f"no query block in {path}")
    return match.group(1)


def _count(value: object) -> int:
    number = float(value)  # type: ignore[arg-type]
    if not number.is_integer():
        raise ValueError(f"request count {value!r} is not a whole number")
    return int(number)


def _row_from_series(series: dict[str, object]) -> RequestRow:
    labels = dict(str(label).split("=", 1) for label in series["group-labels"])  # type: ignore[attr-defined]  # object-typed JSON
    points = series.get("points", [])
    values = [p[1] if isinstance(p, (list, tuple)) else p for p in points]  # type: ignore[attr-defined]
    total = sum(float(v) for v in values if v is not None)
    return RequestRow(labels["sessionId"], labels["householdId"], labels["deviceId"], labels["lightstep.trace_id"], _count(total))


def _mapped(build: Callable[[dict], RequestRow], rows: Iterable[dict]) -> list[RequestRow]:
    try:
        return [build(r) for r in rows]
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError) as exc:
        raise LightstepSourceError(f"malformed Lightstep row: {exc!r}") from exc


def _safe(value: str) -> str:
    if not _SAFE_VALUE.fullmatch(value):
        raise LightstepSourceError(f"unsafe value for a Lightstep query: {value!r}")
    return value
