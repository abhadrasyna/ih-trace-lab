"""Pure device and policy analysis over the mDRM exports: ``brRef`` against security level, device and content failures.

No file or network I/O. A request is one distinct mdrmfe ``fcId``; it fails unless mdrmfe is 201 and every
LRM row for it is 200. ``brRef=LOW`` is a Widevine L3 (SD only) policy, so an L1 device that got ``LOW`` lost HD.
FairPlay and PlayReady have no L1/L3 split, so they never count towards the HD loss.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from lib.drm_exports import CdmRow, LrmRow, MdrmfeRow
from lib.drm_funnel import license_outcome, request_ok, session_kind

UNKNOWN = "unknown"
LOW = "LOW"
LEVEL_L1 = "L1"
DIMENSIONS = ("device", "household", "content")


@dataclass(frozen=True)
class HdLoss:
    widevine_requests: int
    l1_requests: int
    l1_low_requests: int
    widevine_sessions: int
    l1_low_sessions: int


@dataclass(frozen=True)
class GroupStat:
    key: str
    requests: int
    failures: int

    @property
    def failure_rate(self) -> float:
        return self.failures / self.requests if self.requests else 0.0


def _lrm_status(lrm: Sequence[LrmRow]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for r in lrm:
        if r.fcid:
            grouped[r.fcid].append(r.status_code)
    return grouped


def _requests(mdrmfe: Sequence[MdrmfeRow]) -> list[MdrmfeRow]:
    """First row per distinct ``fcId``."""
    seen: dict[str, MdrmfeRow] = {}
    for r in mdrmfe:
        if r.fcid:
            seen.setdefault(r.fcid, r)
    return list(seen.values())


def _cdm_by_fcid(cdm: Sequence[CdmRow]) -> dict[str, CdmRow]:
    out: dict[str, CdmRow] = {}
    for r in cdm:
        if r.fcid:
            out.setdefault(r.fcid, r)
    return out


def _br(row: MdrmfeRow) -> str:
    return row.br_ref.upper() or UNKNOWN


def _type(row: MdrmfeRow) -> str:
    return row.drm_type.lower() or UNKNOWN


def _level(row: MdrmfeRow, cdm: Mapping[str, CdmRow]) -> str:
    found = cdm.get(row.fcid)
    return found.security_level.upper() if found and found.drm_type == "widevine" and found.security_level else UNKNOWN


def br_ref_by_drm_type(mdrmfe: Sequence[MdrmfeRow]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for r in _requests(mdrmfe):
        out[_type(r)][_br(r)] += 1
    return {t: dict(sorted(c.items())) for t, c in sorted(out.items())}


def widevine_level_br_ref(mdrmfe: Sequence[MdrmfeRow], cdm: Sequence[CdmRow]) -> dict[str, dict[str, int]]:
    """Widevine requests by security level (from the CDM export) and ``brRef``."""
    by_fcid = _cdm_by_fcid(cdm)
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for r in _requests(mdrmfe):
        if _type(r) == "widevine":
            out[_level(r, by_fcid)][_br(r)] += 1
    return {lvl: dict(sorted(c.items())) for lvl, c in sorted(out.items())}


def widevine_hd_loss(mdrmfe: Sequence[MdrmfeRow], cdm: Sequence[CdmRow]) -> HdLoss:
    """Widevine requests and sessions where the device is L1 but the token says ``LOW``."""
    by_fcid = _cdm_by_fcid(cdm)
    widevine = [r for r in _requests(mdrmfe) if _type(r) == "widevine"]
    l1 = [r for r in widevine if _level(r, by_fcid) == LEVEL_L1]
    l1_low = [r for r in l1 if _br(r) == LOW]
    sessions = {r.session_id for r in widevine if r.session_id}
    return HdLoss(len(widevine), len(l1), len(l1_low), len(sessions), len({r.session_id for r in l1_low if r.session_id}))


def _stats(groups: Mapping[str, list[bool]]) -> list[GroupStat]:
    return [GroupStat(k, len(v), v.count(False)) for k, v in groups.items()]


def device_split(
    mdrmfe: Sequence[MdrmfeRow], lrm: Sequence[LrmRow], cdm: Sequence[CdmRow], drm_type: str
) -> list[GroupStat]:
    """Requests and failures of one DRM type by CDM device (FairPlay: type and OS; others: make, model, platform)."""
    status, by_fcid = _lrm_status(lrm), _cdm_by_fcid(cdm)
    groups: dict[str, list[bool]] = defaultdict(list)
    for r in _requests(mdrmfe):
        if _type(r) != drm_type:
            continue
        c = by_fcid.get(r.fcid)
        key = " / ".join(x for x in (c.make, c.model, c.platform) if x) if c else UNKNOWN
        groups[key or UNKNOWN].append(request_ok(r, status))
    return sorted(_stats(groups), key=lambda g: (-g.requests, g.key))


def outcome_by_kind(mdrmfe: Sequence[MdrmfeRow], lrm: Sequence[LrmRow]) -> dict[str, dict[str, int]]:
    """Session license outcome split by VOD, linear or other, counting sessions with an mdrmfe request."""
    status = _lrm_status(lrm)
    by_session: dict[str, list[MdrmfeRow]] = defaultdict(list)
    for r in mdrmfe:
        if r.session_id:
            by_session[r.session_id].append(r)
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for session_id, rows in by_session.items():
        out[session_kind(session_id)][license_outcome(rows, status)] += 1
    return {k: dict(sorted(c.items())) for k, c in sorted(out.items())}


def rank_failures(
    mdrmfe: Sequence[MdrmfeRow], lrm: Sequence[LrmRow], cdm: Sequence[CdmRow], dimension: str, min_volume: int = 5,
) -> list[GroupStat]:
    """Groups with failures, ranked by failure count then rate; groups under ``min_volume`` requests are hidden."""
    if dimension not in DIMENSIONS:
        raise ValueError(f"unknown dimension {dimension!r}; expected one of {DIMENSIONS}")
    status, by_fcid = _lrm_status(lrm), _cdm_by_fcid(cdm)
    keyers: dict[str, Callable[[MdrmfeRow], str]] = {
        "device": lambda r: _device_key(r, by_fcid),
        "household": lambda r: r.household_id or UNKNOWN,
        "content": lambda r: r.content_id or UNKNOWN,
    }
    groups: dict[str, list[bool]] = defaultdict(list)
    for r in _requests(mdrmfe):
        groups[keyers[dimension](r)].append(request_ok(r, status))
    stats = [g for g in _stats(groups) if g.requests >= min_volume and g.failures > 0]
    return sorted(stats, key=lambda g: (-g.failures, -g.failure_rate, g.key))


def _device_key(row: MdrmfeRow, cdm: Mapping[str, CdmRow]) -> str:
    c = cdm.get(row.fcid)
    if not c:
        return UNKNOWN
    return " ".join(x for x in (c.make, c.model, _level(row, cdm) if c.drm_type == "widevine" else "") if x) or UNKNOWN


def br_ref_by_date(rows_by_date: Mapping[str, Sequence[MdrmfeRow]]) -> tuple[dict[str, dict[str, int]], bool]:
    """``brRef`` counts per date and whether a single value is used on every date (constant policy)."""
    per_date = {d: dict(sorted(Counter(_br(r) for r in _requests(rows)).items())) for d, rows in sorted(rows_by_date.items())}
    values = {v for counts in per_date.values() for v in counts}
    return per_date, len(values) <= 1
