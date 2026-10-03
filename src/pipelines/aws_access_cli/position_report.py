"""Business logic for deriving the Shaka 1xxx position report."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.lib.athena.protocols import AthenaClient
from src.pipelines.aws_access_cli.catalog import QueryCatalog, comma_join_quoted
from src.pipelines.aws_access_cli.tenants import TenantConfig

POSITION_NOT_MOVED_THRESHOLD_SECONDS = 1.0
_SESSION_ID_BATCH_SIZE = 250
_NON_LIFECYCLE_EVENT_IDS = frozenset({"PLAYER_POSITION", "APP_KEEPALIVE"})
_MM_SS_PART_RE = re.compile(r"\d+(\.\d+)?")


@dataclass(frozen=True)
class SessionPositionReportRow:
    session_id: str
    state_sequence: str = ""
    error_codes: str = ""
    error_descriptions: str = ""
    error_count: int = 0
    first_error_time: str = ""
    min_position: float | None = None
    max_position: float | None = None
    position_not_moved: bool | None = None


def parse_position_seconds(raw: str, eventid: str = "") -> float | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        parts = raw.split(":")
        if not (2 <= len(parts) <= 3) or not all(_MM_SS_PART_RE.fullmatch(part) for part in parts):
            return None
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
    if eventid == "APP_KEEPALIVE":
        seconds = seconds / 1000.0
    if not math.isfinite(seconds):
        return None
    return seconds


def _batched(values: list[str], batch_size: int = _SESSION_ID_BATCH_SIZE) -> list[list[str]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def _parse_eventdata(raw_eventdata: str) -> dict[str, str] | None:
    if not raw_eventdata:
        return None
    try:
        payload = json.loads(raw_eventdata)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return {
        key: ""
        if value is None
        else value
        if isinstance(value, str)
        else json.dumps(value, sort_keys=True)
        if isinstance(value, (dict, list))
        else str(value)
        for key, value in payload.items()
    }


def derive_session_rows(debug_event_rows: list[dict[str, str]]) -> list[SessionPositionReportRow]:
    grouped: dict[str, list[tuple[str, str, str, str, str, str]]] = {}
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    for row in debug_event_rows:
        session_id = (row.get("session_id") or "").strip()
        if not session_id:
            continue
        eventid = row.get("eventid", "")
        datetime_str = row.get("datetime", "")
        eventdata = _parse_eventdata(row.get("eventdata", ""))
        if eventdata is None:
            continue
        state = eventdata.get("eventtype") or eventdata.get("state") or ""
        errorcode = eventdata.get("errorcode", "")
        errordescription = eventdata.get("errordescription", "")
        position = eventdata.get("position", "")
        dedup_key = (session_id, eventid, state, position, errorcode, errordescription, datetime_str)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        grouped.setdefault(session_id, []).append((datetime_str, eventid, state, errorcode, errordescription, position))

    rows: list[SessionPositionReportRow] = []
    for session_id, events in grouped.items():
        events.sort(key=lambda item: item[0])
        labels: list[str] = []
        errors: list[tuple[str, str, str]] = []
        positions: list[float] = []
        for datetime_str, eventid, state, errorcode, errordescription, position in events:
            parsed = parse_position_seconds(position, eventid=eventid)
            if parsed is not None:
                positions.append(parsed)
            if eventid in _NON_LIFECYCLE_EVENT_IDS:
                continue
            if errorcode:
                labels.append(f"ERROR({errorcode})")
                errors.append((datetime_str, errorcode, errordescription))
            else:
                labels.append(state or eventid)
        min_position = min(positions) if positions else None
        max_position = max(positions) if positions else None
        position_not_moved = (
            None
            if len(positions) < 2 or min_position is None or max_position is None
            else (max_position - min_position) < POSITION_NOT_MOVED_THRESHOLD_SECONDS
        )
        rows.append(
            SessionPositionReportRow(
                session_id=session_id,
                state_sequence="->".join(labels),
                error_codes=";".join(error[1] for error in errors),
                error_descriptions=";".join(error[2] for error in errors),
                error_count=len(errors),
                first_error_time=errors[0][0] if errors else "",
                min_position=min_position,
                max_position=max_position,
                position_not_moved=position_not_moved,
            )
        )
    return sorted(rows, key=lambda row: row.session_id)


def run_position_report(
    athena: AthenaClient,
    catalog: QueryCatalog,
    tenant: TenantConfig,
    date_value: str,
    *,
    table_override: str | None = None,
) -> list[dict[str, str]]:
    next_date = (datetime.strptime(date_value, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    session_id_sql = catalog.render(
        "aws-access-cli_error_1xxx_session_ids",
        {
            "database_identifier": tenant.database,
            "table_identifier": table_override or tenant.debug_events_table,
            "error_codes": ", ".join(f"'{code}'" for code in range(1001, 1011)),
            "date": date_value,
            "next_date": next_date,
        },
    )
    session_id_rows = athena.fetch_results(athena.start_query(session_id_sql, {})).rows
    session_ids = sorted({row["session_id"] for row in session_id_rows if row.get("session_id")})
    if not session_ids:
        return []
    playback_rows: dict[str, dict[str, str]] = {}
    debug_rows: list[dict[str, str]] = []
    for session_batch in _batched(session_ids):
        id_list = comma_join_quoted(session_batch)
        playback_sql = catalog.render(
            "aws-access-cli_playback_outcome",
            {"database_identifier": tenant.database, "date": date_value, "session_filter": f"AND parent_session_id IN ({id_list})"},
        )
        for row in athena.fetch_results(athena.start_query(playback_sql, {})).rows:
            session_id = row.get("sessionId", "")
            if session_id:
                playback_rows[session_id] = row
        debug_sql = catalog.render(
            "aws-access-cli_session_debug_events",
            {
                "database_identifier": tenant.database,
                "table_identifier": table_override or tenant.debug_events_table,
                "id_list": id_list,
                "start_date": date_value,
                "end_date_exclusive": next_date,
            },
        )
        debug_rows.extend(athena.fetch_results(athena.start_query(debug_sql, {})).rows)
    derived_rows = derive_session_rows(debug_rows)
    report_rows: list[dict[str, str]] = []
    for derived in derived_rows:
        playback = playback_rows.get(derived.session_id, {})
        report_rows.append(
            {
                "householdId": playback.get("householdId", ""),
                "deviceId": playback.get("deviceId", ""),
                "sessionId": derived.session_id,
                "start_time": playback.get("event_start", ""),
                "error_codes": derived.error_codes,
                "error_descriptions": derived.error_descriptions,
                "state_sequence": derived.state_sequence,
                "min_position": "" if derived.min_position is None else str(derived.min_position),
                "max_position": "" if derived.max_position is None else str(derived.max_position),
                "position_not_moved": "" if derived.position_not_moved is None else str(derived.position_not_moved),
            }
        )
    return report_rows
