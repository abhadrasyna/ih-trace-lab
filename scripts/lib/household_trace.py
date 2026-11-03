"""Pure logic that joins one household's SM-VOD sessions to their mDRM licence chain and client debug events.

No I/O and no network: callers pass in Lightstep series (``group-labels`` + ``points``) and Athena debug-event rows.
Join keys: ``sm-vod`` ``sessionId`` == ``go-mdrmfe`` ``drmAuthToken.sessionId``; ``go-mdrmfe`` ``fcid`` == US ``fcId``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,100}$")
_FCID_PATTERN = re.compile(r"^[A-Za-z0-9]{8,64}$")

Series = Mapping[str, object]

# Each outcome is prefixed with the system that produced the evidence; that prefix is the `evidence_layer` column.
OUTCOME_ATHENA_SESSION_PLAYER_ERROR = "ATHENA_SESSION_PLAYER_ERROR"
OUTCOME_ATHENA_SESSION_PLAYED = "ATHENA_SESSION_PLAYED"
OUTCOME_ATHENA_SESSION_OTHER_ENDREASON = "ATHENA_SESSION_OTHER_ENDREASON"
OUTCOME_SMVOD_CREATE_NON_2XX = "SMVOD_CREATE_NON_2XX"
OUTCOME_MDRMFE_SPAN_NOT_SEEN = "MDRMFE_SPAN_NOT_SEEN"
OUTCOME_MDRMFE_STATUS_NON_2XX = "MDRMFE_STATUS_NON_2XX"
OUTCOME_MDRM_US_HOP_NON_2XX = "MDRM_US_HOP_NON_2XX"
OUTCOME_MDRM_LICENSE_OK_NO_ATHENA = "MDRM_LICENSE_OK_NO_ATHENA"

EVIDENCE_LAYER = {
    OUTCOME_ATHENA_SESSION_PLAYER_ERROR: "ATHENA",
    OUTCOME_ATHENA_SESSION_PLAYED: "ATHENA",
    OUTCOME_ATHENA_SESSION_OTHER_ENDREASON: "ATHENA",
    OUTCOME_SMVOD_CREATE_NON_2XX: "SMVOD",
    OUTCOME_MDRMFE_SPAN_NOT_SEEN: "MDRMFE",
    OUTCOME_MDRMFE_STATUS_NON_2XX: "MDRMFE",
    OUTCOME_MDRM_US_HOP_NON_2XX: "MDRM",
    OUTCOME_MDRM_LICENSE_OK_NO_ATHENA: "MDRM",
}

COLUMNS = (
    "first_seen_utc", "sessionId", "contentId", "content_title", "clientIp", "sm_vod_create", "sm_vod_teardown",
    "drmType", "brRef", "mdrmfe_status", "fcid", "licence_chain", "drm_make", "drm_model",
    "drm_platform", "drm_security_level", "unified_content_id", "unified_endreason", "play_seconds",
    "debug_error_code", "debug_error_text", "debug_shaka_error", "debug_user_agent", "outcome", "evidence_layer",
)


@dataclass
class SessionRow:
    session_id: str
    first_seen_ms: int | None = None
    content_id: str = ""
    client_ip: str = ""
    create_status: str = ""
    teardown_status: str = ""
    drm_type: str = ""
    br_ref: str = ""
    mdrmfe_status: str = ""
    fcid: str = ""
    chain: str = ""
    drm: dict[str, str] = field(default_factory=dict)
    debug: dict[str, str] = field(default_factory=dict)
    unified: dict[str, str] = field(default_factory=dict)


def validate_hhid(hhid: str) -> str:
    """Returns the stripped household id; raises ValueError for anything that is not a plain id token."""
    value = hhid.strip()
    if not _ID_PATTERN.fullmatch(value):
        raise ValueError(f"householdId {hhid!r} is not a plain id (20-100 chars of A-Z a-z 0-9 _ -)")
    return value


def sm_vod_uql(hhid: str) -> str:
    return (
        f'spans count | delta | filter service == "sm-vod" && householdId == "{validate_hhid(hhid)}" '
        '| group_by ["deviceId", "session.clientIp", "sessionId", "http.status_code", "operation", "contentId"], sum'
    )


def mdrmfe_uql(hhid: str) -> str:
    return (
        f'spans count | delta | filter service == "go-mdrmfe" && drmAuthToken.householdId == "{validate_hhid(hhid)}" '
        '| group_by ["drmAuthToken.sessionId", "drmAuthToken.deviceId", "drmAuthToken.drmType", "drmAuthToken.brRef", '
        '"http.status_code", "fcid"], sum'
    )


def us_chain_uql(fcids: Iterable[str]) -> str:
    """Raises ValueError for an empty or malformed fcid list (they are interpolated into the query)."""
    ids = sorted({f.strip() for f in fcids if f.strip()})
    if not ids:
        raise ValueError("no fcid to query")
    bad = [f for f in ids if not _FCID_PATTERN.fullmatch(f)]
    if bad:
        raise ValueError(f"malformed fcid(s): {bad}")
    flt = " || ".join(f'fcId == "{f}"' for f in ids)
    return (
        f"spans count | delta | filter {flt} | group_by [\"fcId\", \"service\", \"http.status_code\", "
        '"drmInfo.DeviceType", "drmInfo.Make", "drmInfo.Model", "drmInfo.Platform", "drmInfo.SecurityLevel"], sum'
    )


def labels(series: Series) -> dict[str, str]:
    """``["k=v", ...]`` group labels -> dict (values may contain '=')."""
    out: dict[str, str] = {}
    for item in series.get("group-labels", []):  # type: ignore[attr-defined]
        key, sep, value = str(item).partition("=")
        if sep:
            out[key] = value
    return out


def first_point_ms(series: Series) -> int | None:
    """Earliest timestamp (ms) whose value is positive."""
    stamps = [int(p[0]) for p in series.get("points", []) if len(p) > 1 and float(p[1]) > 0]  # type: ignore[attr-defined]
    return min(stamps) if stamps else None


def _status_ok(status: str) -> bool:
    return status.isdigit() and 200 <= int(status) < 300


def device_ids(sm_vod: Sequence[Series], mdrmfe: Sequence[Series]) -> list[str]:
    """Distinct non-empty deviceIds seen on the household's sm-vod and go-mdrmfe series, sorted."""
    found = {labels(s).get("deviceId", "") for s in sm_vod} | {labels(s).get("drmAuthToken.deviceId", "") for s in mdrmfe}
    return sorted(d for d in found if d)


def build_sessions(sm_vod: Sequence[Series], mdrmfe: Sequence[Series]) -> dict[str, SessionRow]:
    """One row per ``sessionId`` from the sm-vod (create/teardown) and go-mdrmfe series."""
    rows: dict[str, SessionRow] = {}
    for series in sm_vod:
        lab = labels(series)
        sid = lab.get("sessionId", "")
        if not sid:
            continue
        row = rows.setdefault(sid, SessionRow(sid))
        stamp = first_point_ms(series)
        if stamp is not None and (row.first_seen_ms is None or stamp < row.first_seen_ms):
            row.first_seen_ms = stamp
        if lab.get("contentId"):
            row.content_id = lab["contentId"]
        if lab.get("session.clientIp"):
            row.client_ip = lab["session.clientIp"]
        if lab.get("operation") == "POST":
            row.create_status = lab.get("http.status_code", "")
        elif lab.get("operation") == "DELETE":
            row.teardown_status = lab.get("http.status_code", "")
    for series in mdrmfe:
        lab = labels(series)
        sid = lab.get("drmAuthToken.sessionId", "")
        if not sid:
            continue
        row = rows.setdefault(sid, SessionRow(sid))
        stamp = first_point_ms(series)
        if row.first_seen_ms is None and stamp is not None:
            row.first_seen_ms = stamp
        row.drm_type = lab.get("drmAuthToken.drmType", "")
        row.br_ref = lab.get("drmAuthToken.brRef", "")
        row.mdrmfe_status = lab.get("http.status_code", "")
        row.fcid = lab.get("fcid", "")
    return rows


def attach_chain(rows: Mapping[str, SessionRow], us_series: Sequence[Series]) -> None:
    """Fills ``chain`` ("service:status;...") and the CDM device on each row from the US series, keyed by fcid."""
    by_fcid: dict[str, list[dict[str, str]]] = {}
    for series in us_series:
        lab = labels(series)
        if lab.get("fcId"):
            by_fcid.setdefault(lab["fcId"], []).append(lab)
    for row in rows.values():
        entries = by_fcid.get(row.fcid, []) if row.fcid else []
        row.chain = ";".join(sorted(f"{e.get('service', '')}:{e.get('http.status_code', '')}" for e in entries))
        for e in entries:
            if e.get("drmInfo.Model") or e.get("drmInfo.Make"):
                row.drm = {
                    "make": e.get("drmInfo.Make", ""), "model": e.get("drmInfo.Model", ""),
                    "platform": e.get("drmInfo.Platform", ""), "security_level": e.get("drmInfo.SecurityLevel", ""),
                }


def summarize_athena(events: Iterable[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    """Per ``sessionid``: first PLAYER_ERROR (code/text/shaka/user agent) and whether a non-STOPPED state was seen."""
    out: dict[str, dict[str, str]] = {}
    for event in events:
        try:
            data = json.loads(event.get("eventdata") or "{}")
        except json.JSONDecodeError:
            continue
        sid = str(data.get("sessionid") or "")
        if not sid:
            continue
        entry = out.setdefault(sid, {"error_code": "", "error_text": "", "shaka_error": "", "user_agent": ""})
        if event.get("eventid", "") == "PLAYER_ERROR" and not entry["error_code"]:
            desc = data.get("errordescription") or {}
            shaka = desc.get("shakaerror") or {} if isinstance(desc, dict) else {}
            entry["error_code"] = str(data.get("errorcode", ""))
            entry["error_text"] = str(desc.get("errordescription", "")) if isinstance(desc, dict) else str(desc)
            entry["shaka_error"] = str(shaka.get("message", ""))
            entry["user_agent"] = str(desc.get("user_agent", "")) if isinstance(desc, dict) else ""
    return out


def _parse_ts(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def summarize_unified(rows: Iterable[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    """Per ``parent_session_id``: title, content id, device, first start, endreason and PLAY seconds from unified_sessions rows.

    The PLAY row is the session summary; its endreason wins over the REQUEST_VIEWING row's.
    """
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        sid = row.get("parent_session_id", "")
        if not sid:
            continue
        entry = out.setdefault(sid, {"title": "", "content_id": "", "device_id": "", "first_start": "",
                                     "endreason": "", "play_seconds": "", "has_play": "", "request_endreason": ""})
        for key, column in (("title", "content"), ("content_id", "content_id"), ("device_id", "device_id")):
            if row.get(column):
                entry[key] = row[column]
        start = row.get("event_start", "")
        if start and (not entry["first_start"] or start < entry["first_start"]):
            entry["first_start"] = start
        if row.get("event_type") == "PLAY":
            entry["has_play"] = "yes"
            entry["endreason"] = row.get("endreason", "")
            begin, end = _parse_ts(start), _parse_ts(row.get("event_end", ""))
            if begin and end:
                entry["play_seconds"] = f"{(end - begin).total_seconds():.0f}"
        elif row.get("event_type") == "REQUEST_VIEWING":
            entry["request_endreason"] = row.get("endreason", "")
    for entry in out.values():
        entry["endreason"] = entry["endreason"] or entry["request_endreason"]
    return out


def pick_debug_suffix(first_start: str, existing_suffixes: Iterable[str]) -> str:
    """Suffix of the existing month table covering a ``YYYY-MM-DD hh:mm:ss`` time, or ``""`` for the unsuffixed (current) table.

    Matches month abbreviation + 2-digit year, so ``sept26`` matches September 2026. ValueError if the time is unparsable.
    """
    moment = _parse_ts(first_start)
    if moment is None:
        raise ValueError(f"cannot derive debug table from {first_start!r}")
    month, year = moment.strftime("%b").lower(), moment.strftime("%y")
    for suffix in sorted(existing_suffixes):
        if suffix.startswith(month) and suffix.endswith(year):
            return suffix
    return ""


def error_sessions_by_table(
    rows: Mapping[str, SessionRow], suffix_override: str | None, existing_suffixes: Iterable[str],
) -> dict[str, dict[str, object]]:
    """Groups sessions whose unified endreason is PLAYER_ERROR by debug table suffix (``""`` = unsuffixed table).

    Value: ``{"devices": sorted device ids, "date_from": ..., "date_to": ..., "sessions": sorted ids}``.
    Needs a device id and start time on each error session; raises ValueError otherwise.
    """
    existing = list(existing_suffixes)
    groups: dict[str, dict[str, object]] = {}
    for sid, row in rows.items():
        if row.unified.get("endreason") != "PLAYER_ERROR":
            continue
        device, start = row.unified.get("device_id", ""), row.unified.get("first_start", "")
        if not device or not start:
            raise ValueError(f"session {sid} has a PLAYER_ERROR but no device_id/event_start in unified_sessions")
        suffix = suffix_override if suffix_override is not None else pick_debug_suffix(start, existing)
        group = groups.setdefault(suffix, {"devices": set(), "date_from": start[:10], "date_to": start[:10], "sessions": []})
        group["devices"].add(device)  # type: ignore[attr-defined]
        group["date_from"], group["date_to"] = min(group["date_from"], start[:10]), max(group["date_to"], start[:10])  # type: ignore[type-var]
        group["sessions"].append(sid)  # type: ignore[attr-defined]
    for group in groups.values():
        group["devices"], group["sessions"] = sorted(group["devices"]), sorted(group["sessions"])  # type: ignore[type-var]
    return groups


def classify(row: SessionRow, athena_loaded: bool) -> str:
    """unified_sessions evidence wins when the session is in it; otherwise judge from the Lightstep licence chain."""
    if athena_loaded and row.unified:
        if row.unified.get("endreason") == "PLAYER_ERROR":
            return OUTCOME_ATHENA_SESSION_PLAYER_ERROR
        if row.unified.get("has_play"):
            return OUTCOME_ATHENA_SESSION_PLAYED
        return OUTCOME_ATHENA_SESSION_OTHER_ENDREASON
    if row.create_status and not _status_ok(row.create_status):
        return OUTCOME_SMVOD_CREATE_NON_2XX
    if not row.mdrmfe_status:
        return OUTCOME_MDRMFE_SPAN_NOT_SEEN
    if not _status_ok(row.mdrmfe_status):
        return OUTCOME_MDRMFE_STATUS_NON_2XX
    if row.chain and not all(_status_ok(p.rsplit(":", 1)[-1]) for p in row.chain.split(";")):
        return OUTCOME_MDRM_US_HOP_NON_2XX
    return OUTCOME_MDRM_LICENSE_OK_NO_ATHENA


def to_table(rows: Mapping[str, SessionRow], athena_loaded: bool, fmt_time) -> list[dict[str, str]]:
    """Rows sorted by first-seen time, one dict per session keyed by ``COLUMNS``; ``fmt_time(ms)`` renders the time."""
    table = []
    for row in sorted(rows.values(), key=lambda r: (r.first_seen_ms is None, r.first_seen_ms or 0, r.session_id)):
        outcome = classify(row, athena_loaded)
        table.append({
            "first_seen_utc": fmt_time(row.first_seen_ms) if row.first_seen_ms is not None else "",
            "sessionId": row.session_id, "contentId": row.content_id, "content_title": row.unified.get("title", ""),
            "clientIp": row.client_ip,
            "sm_vod_create": row.create_status, "sm_vod_teardown": row.teardown_status,
            "drmType": row.drm_type, "brRef": row.br_ref, "mdrmfe_status": row.mdrmfe_status, "fcid": row.fcid,
            "licence_chain": row.chain, "drm_make": row.drm.get("make", ""), "drm_model": row.drm.get("model", ""),
            "drm_platform": row.drm.get("platform", ""), "drm_security_level": row.drm.get("security_level", ""),
            "unified_content_id": row.unified.get("content_id", ""), "unified_endreason": row.unified.get("endreason", ""),
            "play_seconds": row.unified.get("play_seconds", ""),
            "debug_error_code": row.debug.get("error_code", ""), "debug_error_text": row.debug.get("error_text", ""),
            "debug_shaka_error": row.debug.get("shaka_error", ""), "debug_user_agent": row.debug.get("user_agent", ""),
            "outcome": outcome, "evidence_layer": EVIDENCE_LAYER[outcome],
        })
    return table
