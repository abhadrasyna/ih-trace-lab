"""Pure logic that joins one household's SM-VOD sessions to their mDRM licence chain and client debug events.

No I/O and no network: callers pass in Lightstep series (``group-labels`` + ``points``) and Athena debug-event rows.
Join keys: ``sm-vod`` ``sessionId`` == ``go-mdrmfe`` ``drmAuthToken.sessionId``; ``go-mdrmfe`` ``fcid`` == US ``fcId``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

_ID = re.compile(r"^[A-Za-z0-9_-]{20,100}$")
_FCID = re.compile(r"^[A-Za-z0-9]{8,64}$")

Series = Mapping[str, object]

OUTCOME_FAILED = "FAILED"
OUTCOME_PLAYED = "PLAYED"
OUTCOME_LICENSE_OK = "LICENSE_OK_PLAYBACK_UNCONFIRMED"
OUTCOME_LICENSE_DENIED = "LICENSE_DENIED"
OUTCOME_NO_LICENSE = "NO_LICENSE_REQUEST"
OUTCOME_NO_ATHENA = "NO_PLAYER_OUTCOME"

COLUMNS = (
    "first_seen_utc", "sessionId", "contentId", "clientIp", "sm_vod_create", "sm_vod_teardown",
    "drmType", "brRef", "mdrmfe_status", "fcid", "licence_chain", "drm_make", "drm_model",
    "drm_platform", "drm_security_level", "athena_error_code", "athena_error_text", "athena_shaka_error",
    "athena_user_agent", "outcome",
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
    athena: dict[str, str] = field(default_factory=dict)


def validate_hhid(hhid: str) -> str:
    """Returns the stripped household id; raises ValueError for anything that is not a plain id token."""
    value = hhid.strip()
    if not _ID.fullmatch(value):
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
    bad = [f for f in ids if not _FCID.fullmatch(f)]
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
        entry = out.setdefault(sid, {"error_code": "", "error_text": "", "shaka_error": "", "user_agent": "", "played": ""})
        eid = event.get("eventid", "")
        if eid == "PLAYER_ERROR" and not entry["error_code"]:
            desc = data.get("errordescription") or {}
            shaka = desc.get("shakaerror") or {} if isinstance(desc, dict) else {}
            entry["error_code"] = str(data.get("errorcode", ""))
            entry["error_text"] = str(desc.get("errordescription", "")) if isinstance(desc, dict) else str(desc)
            entry["shaka_error"] = str(shaka.get("message", ""))
            entry["user_agent"] = str(desc.get("user_agent", "")) if isinstance(desc, dict) else ""
        elif eid == "PLAYER_STATE_CHANGE" and data.get("state") not in (None, "", "STOPPED"):
            entry["played"] = "yes"
    return out


def classify(row: SessionRow, athena_loaded: bool) -> str:
    """Athena evidence wins when loaded; otherwise judge from the Lightstep licence chain only."""
    if athena_loaded:
        info = row.athena
        if info.get("error_code"):
            return OUTCOME_FAILED
        if info.get("played"):
            return OUTCOME_PLAYED
        if info:
            return OUTCOME_NO_ATHENA
    if not row.mdrmfe_status:
        return OUTCOME_NO_LICENSE
    if not _status_ok(row.mdrmfe_status) or (row.chain and not all(_status_ok(p.rsplit(":", 1)[-1]) for p in row.chain.split(";"))):
        return OUTCOME_LICENSE_DENIED
    return OUTCOME_LICENSE_OK


def to_table(rows: Mapping[str, SessionRow], athena_loaded: bool, fmt_time) -> list[dict[str, str]]:
    """Rows sorted by first-seen time, one dict per session keyed by ``COLUMNS``; ``fmt_time(ms)`` renders the time."""
    table = []
    for row in sorted(rows.values(), key=lambda r: (r.first_seen_ms is None, r.first_seen_ms or 0, r.session_id)):
        table.append({
            "first_seen_utc": fmt_time(row.first_seen_ms) if row.first_seen_ms is not None else "",
            "sessionId": row.session_id, "contentId": row.content_id, "clientIp": row.client_ip,
            "sm_vod_create": row.create_status, "sm_vod_teardown": row.teardown_status,
            "drmType": row.drm_type, "brRef": row.br_ref, "mdrmfe_status": row.mdrmfe_status, "fcid": row.fcid,
            "licence_chain": row.chain, "drm_make": row.drm.get("make", ""), "drm_model": row.drm.get("model", ""),
            "drm_platform": row.drm.get("platform", ""), "drm_security_level": row.drm.get("security_level", ""),
            "athena_error_code": row.athena.get("error_code", ""), "athena_error_text": row.athena.get("error_text", ""),
            "athena_shaka_error": row.athena.get("shaka_error", ""), "athena_user_agent": row.athena.get("user_agent", ""),
            "outcome": classify(row, athena_loaded),
        })
    return table
