"""Athena-side data for the usage report: sessions, devices seen per household, and playback errors.

Two implementers of `SessionSource` serve one tenant each: `LocalExportSource` (default, reads the ctap-smvod CSV exports) and `LiveAthenaSource` (`--live-athena`). The CLI picks one; neither falls
back to the other.
"""
from __future__ import annotations

import csv
import logging
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from src.lib.logging.redact import redact_params

from .errors import AthenaSourceError
from .roster import Household

LOGGER = logging.getLogger(__name__)

ERROR_OUTCOMES = frozenset({"PLAYER_ERROR"})
QUERIES_DIR = Path(__file__).resolve().parents[3] / "queries" / "athena"
DEFAULT_EXPORT_ROOT = Path(__file__).resolve().parents[3] / "investigations" / "ctap-smvod" / "data" / "athena"
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_\-:.]+$")
_MONTH_SUFFIX = {1: "jan", 2: "feb", 3: "mar", 4: "apr", 5: "may", 6: "jun", 7: "jul", 8: "aug", 9: "sept", 10: "oct", 11: "nov", 12: "dec"}
_LOG_ALLOW = {"tenant", "date", "table"}

QueryRunner = Callable[[str], list[dict[str, str]]]


@dataclass(frozen=True)
class SessionRow:
    session_id: str
    household_id: str
    device_id: str
    content: str
    content_id: str
    outcome: str
    event_start: str
    event_end: str


@dataclass(frozen=True)
class DeviceSeen:
    household_id: str
    device_id: str
    session_count: int
    first_seen: str


@dataclass(frozen=True)
class ErrorRow:
    session_id: str
    error_code: str
    message: str
    position: str
    timestamp: str


class SessionSource(Protocol):
    def fetch_sessions(self, households: Sequence[Household], day: date) -> list[SessionRow]: ...

    def fetch_household_devices(self, household: Household, day: date) -> list[DeviceSeen]: ...

    def fetch_errors(self, sessions: Sequence[SessionRow], day: date) -> list[ErrorRow]: ...


def errored_sessions(sessions: Iterable[SessionRow]) -> list[SessionRow]:
    return [s for s in sessions if s.outcome in ERROR_OUTCOMES]


def client_id(device_id: str, household_id: str) -> str:
    return f"{device_id}:{household_id}"


def debug_table_name(athena_tenant_id: str, day: date, today: date, existing_tables: Iterable[str]) -> str:
    """Current month uses the unsuffixed table; an older month uses its `_<mon><yy>` table, which must exist (note `sept`)."""
    base = f"{athena_tenant_id}_ccl_debug_events"
    if (day.year, day.month) == (today.year, today.month):
        return base
    table = f"{base}_{_MONTH_SUFFIX[day.month]}{day:%y}"
    if table not in set(existing_tables):
        raise AthenaSourceError(f"debug-events table {table} not found for {day}")
    return table


def _pairs(households: Sequence[Household]) -> set[tuple[str, str]]:
    return {(h.hhid, m.device_id) for h in households for m in h.members}


def _check_tenant(tenant: str, households: Iterable[Household]) -> None:
    for household in households:
        if household.tenant != tenant:
            raise AthenaSourceError(f"household {household.hhid} is tenant {household.tenant}, source is {tenant}")


class LocalExportSource:
    """Reads the tenant-wide CSV exports under `<root>/<TENANT>/` and keeps only roster rows."""

    def __init__(self, tenant: str, root: Path = DEFAULT_EXPORT_ROOT) -> None:
        self._tenant = tenant
        self._dir = root / tenant

    def fetch_sessions(self, households: Sequence[Household], day: date) -> list[SessionRow]:
        _check_tenant(self._tenant, households)
        pairs = _pairs(households)
        return [s for s in self._read_sessions(day) if (s.household_id, s.device_id) in pairs]

    def fetch_household_devices(self, household: Household, day: date) -> list[DeviceSeen]:
        _check_tenant(self._tenant, [household])
        mine = [s for s in self._read_sessions(day) if s.household_id == household.hhid]
        counts = Counter(s.device_id for s in mine)
        first = {}
        for s in sorted(mine, key=lambda row: row.event_start):
            first.setdefault(s.device_id, s.event_start)
        return [DeviceSeen(household.hhid, d, counts[d], first[d]) for d in sorted(counts, key=first.get)]

    def fetch_errors(self, sessions: Sequence[SessionRow], day: date) -> list[ErrorRow]:
        wanted = {s.session_id for s in errored_sessions(sessions)}
        if not wanted:
            return []
        rows = self._read_csv(f"{day}_debug_states.csv")
        return [_error_from_debug_state(r) for r in rows if r["eventid"] == "PLAYER_ERROR" and r["sessionId"] in wanted]

    def _read_sessions(self, day: date) -> list[SessionRow]:
        return [
            SessionRow(r["sessionId"], r["householdId"], r["deviceId"], r["content"], "", r["playback_outcome"], r["event_start"], r["event_end"])
            for r in self._read_csv(f"{day}_session.csv")
        ]

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        path = self._dir / name
        if not path.is_file():
            raise AthenaSourceError(f"local export missing: {path}")
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                return list(csv.DictReader(handle))
        except (OSError, csv.Error) as exc:
            raise AthenaSourceError(f"cannot read {path}: {exc}") from exc


def _error_from_debug_state(row: dict[str, str]) -> ErrorRow:
    return ErrorRow(row["sessionId"], row["errorcode"], row["errordescription"], row["position"], row["datetime"])


class LiveAthenaSource:
    """Queries Athena for the roster pairs only, through an injected runner that takes the final SQL."""

    def __init__(self, tenant: str, athena_tenant_id: str, run_query: QueryRunner, today: date, queries_dir: Path = QUERIES_DIR) -> None:
        self._tenant = tenant
        self._database = _safe(f"unified_{athena_tenant_id}")
        self._athena_tenant_id = athena_tenant_id
        self._run = run_query
        self._today = today
        self._queries_dir = queries_dir
        self._tables: list[str] | None = None

    def fetch_sessions(self, households: Sequence[Household], day: date) -> list[SessionRow]:
        _check_tenant(self._tenant, households)
        out: list[SessionRow] = []
        for household in households:
            if not household.members:
                continue
            rows = self._query(
                "usage-tracking-household-device-sessions",
                {
                    "database": self._database,
                    "date_start": str(day),
                    "date_end": str(day),
                    "user_id": _safe(household.hhid),
                    "device_ids_block": ", ".join(f"'{_safe(m.device_id)}'" for m in household.members),
                },
                day,
            )
            out.extend(_session_from_live(r) for r in rows)
        return out

    def fetch_household_devices(self, household: Household, day: date) -> list[DeviceSeen]:
        _check_tenant(self._tenant, [household])
        rows = self._query(
            "usage-tracking-household-all-devices",
            {"database": self._database, "date": str(day), "user_id": _safe(household.hhid)},
            day,
        )
        return [DeviceSeen(household.hhid, r["device_id"], int(r["session_count"]), r["first_seen"]) for r in rows]

    def fetch_errors(self, sessions: Sequence[SessionRow], day: date) -> list[ErrorRow]:
        errored = errored_sessions(sessions)
        if not errored:
            return []
        wanted = {s.session_id for s in errored}
        clients = sorted({client_id(s.device_id, s.household_id) for s in errored})
        rows = self._query(
            "usage-tracking-playback-errors",
            {
                "database": self._database,
                "debug_events_table": self._debug_table(day),
                "datetime_start": f"{day}T00:00:00.000Z",
                "datetime_end": f"{day + timedelta(days=1)}T00:00:00.000Z",
                "client_ids_block": ",\n".join(f"    '{_safe(c)}'" for c in clients),
            },
            day,
        )
        return [ErrorRow(r["session_id"], r["error_code"], r["message"], r["position"], r["datetime"]) for r in rows if r["session_id"] in wanted]

    def _debug_table(self, day: date) -> str:
        if self._tables is None:
            rows = self._execute(f'SHOW TABLES IN "{self._database}"', {"table": "show-tables", "date": str(day)})
            self._tables = [next(iter(r.values())) for r in rows]
        return debug_table_name(self._athena_tenant_id, day, self._today, self._tables)

    def _query(self, slug: str, params: dict[str, str], day: date) -> list[dict[str, str]]:
        sql = _render(_strip_comments((self._queries_dir / f"{slug}.sql").read_text(encoding="utf-8")), params)
        return self._execute(sql, {"table": slug, "date": str(day)})

    def _execute(self, sql: str, log_params: dict[str, str]) -> list[dict[str, str]]:
        shown = redact_params({"tenant": self._tenant, **log_params}, _LOG_ALLOW)
        LOGGER.debug("Athena call start", extra={"call_name": "usage.athena", "params": shown})
        started = time.monotonic()
        try:
            rows = self._run(sql)
        except AthenaSourceError:
            raise
        except Exception as exc:
            raise AthenaSourceError(f"Athena query {log_params.get('table')} failed: {exc}") from exc
        LOGGER.info(
            "Athena call ok",
            extra={"call_name": "usage.athena", "params": shown, "row_count": len(rows), "duration_ms": int((time.monotonic() - started) * 1000)},
        )
        return rows


def _safe(value: str) -> str:
    if not _SAFE_VALUE.match(value):
        raise AthenaSourceError(f"unsafe value for an Athena query: {value!r}")
    return value


def _strip_comments(sql: str) -> str:
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


def _render(sql: str, params: dict[str, str]) -> str:
    for key, value in params.items():
        sql = sql.replace("{{" + key + "}}", value)
    leftover = re.search(r"\{\{(\w+)\}\}", sql)
    if leftover:
        raise AthenaSourceError(f"query placeholder {leftover.group(1)} was not supplied")
    return sql


def _session_from_live(row: dict[str, str]) -> SessionRow:
    return SessionRow(
        row["parent_session_id"], row["user_id"], row["device_id"], row["content"], row.get("content_id", ""), row["endreason"],
        row["event_start"], row["event_end"],
    )
