"""Pure DRM session funnel: sessions -> DRM type -> license outcome -> downstream error.

No file or network I/O; the CLI feeds in rows read by ``lib.drm_exports`` and the pipeline CSVs.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from lib.drm_exports import LrmRow, MdrmfeRow

SOURCE_MERGE = "merge"
SOURCE_DRM_ONLY = "drm_only"

NO_REQUEST = "no_request"
SUCCESS = "success"
FAILED = "failed"
RETRY_THEN_SUCCESS = "retry_then_success"

NO_ERROR = "none"
MIXED = "mixed"
NO_DRM = "none"
KNOWN_DRM_TYPES = ("widevine", "fairplay", "playready")
NAMED_ERRORS = ("3014", "3015", "3016")

MDRMFE_OK = "201"
LRM_OK = "200"


@dataclass(frozen=True)
class SessionInput:
    """One session from the CTAP/SMVOD merge; ``error_codes`` is the raw ``;``-separated column."""

    session_id: str
    error_codes: str = ""


@dataclass(frozen=True)
class FunnelRow:
    opco: str
    date: str
    source: str
    kind: str
    drm_bucket: str
    license_outcome: str
    error_group: str
    sessions: int
    error_code: str = NO_ERROR
    subcategory: str = ""


@dataclass(frozen=True)
class FunnelResult:
    rows: list[FunnelRow]
    totals: dict[str, int]


def session_kind(session_id: str) -> str:
    if session_id.startswith("abr-vod-"):
        return "vod"
    if session_id.startswith("abr-linear-"):
        return "linear"
    return "other"


def error_group(code: str) -> str:
    """3014/3015/3016 by name, other 1xxx/6xxx by family, everything else ``other``; empty is ``none``."""
    code = code.strip()
    if not code:
        return NO_ERROR
    if code in NAMED_ERRORS:
        return code
    if len(code) == 4 and code.isdigit() and code[0] in "16":
        return f"{code[0]}xxx"
    return "other"


def first_error_code(raw: str) -> str:
    for part in raw.split(";"):
        if part.strip():
            return part.strip()
    return ""


def drm_bucket(rows: Sequence[MdrmfeRow]) -> str:
    """``none`` with no mdrmfe row, ``mixed`` for several types, else the type.

    Blank types are ignored when another type is present; unknown or all-blank types are ``other``.
    """
    if not rows:
        return NO_DRM
    types = {r.drm_type.strip().lower() for r in rows} - {""}
    if not types:
        return "other"
    if len(types) > 1:
        return MIXED
    only = next(iter(types))
    return only if only in KNOWN_DRM_TYPES else "other"


def license_outcome(rows: Sequence[MdrmfeRow], lrm_status_by_fcid: dict[str, list[str]]) -> str:
    """``success``: every request ok; ``retry_then_success``: a failure, then a final ok request.

    A request is ok when mdrmfe is 201 and every joined LRM row is 200 (at least one must exist). File
    order stands in for time. Anything else is ``failed``, including a session whose last request failed
    after an earlier success (it did not end with a working license).
    """
    if not rows:
        return NO_REQUEST
    results = [_request_ok(r, lrm_status_by_fcid) for r in rows]
    if all(results):
        return SUCCESS
    return RETRY_THEN_SUCCESS if results[-1] else FAILED


def _request_ok(row: MdrmfeRow, lrm_status_by_fcid: dict[str, list[str]]) -> bool:
    lrm = lrm_status_by_fcid.get(row.fcid, [])
    return row.status_code == MDRMFE_OK and bool(lrm) and all(s == LRM_OK for s in lrm)


def _group_by_session(rows: Iterable[MdrmfeRow]) -> dict[str, list[MdrmfeRow]]:
    grouped: dict[str, list[MdrmfeRow]] = {}
    for row in rows:
        if row.session_id:
            grouped.setdefault(row.session_id, []).append(row)
    return grouped


def _lrm_by_fcid(rows: Iterable[LrmRow]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        if row.fcid:
            grouped.setdefault(row.fcid, []).append(row.status_code)
    return grouped


def first_error_by_session(
    sessions: Sequence[SessionInput], flat_errors: Iterable[tuple[str, str]]
) -> dict[str, str]:
    """First code per session: the merge ``error_codes`` column wins, else the first flat-file row."""
    codes: dict[str, str] = {}
    for session in sessions:
        code = first_error_code(session.error_codes)
        if session.session_id and code and session.session_id not in codes:
            codes[session.session_id] = code
    for session_id, code in flat_errors:
        if session_id and code.strip() and session_id not in codes:
            codes[session_id] = code.strip()
    return codes


def build_funnel(
    opco: str,
    date: str,
    sessions: Sequence[SessionInput],
    mdrmfe: Sequence[MdrmfeRow],
    lrm: Sequence[LrmRow],
    flat_errors: Iterable[tuple[str, str]] = (),
    subcategories: Mapping[str, str] | None = None,
) -> FunnelResult:
    """Count each distinct session once; sessions only in mDRM are added as ``drm_only``."""
    by_session = _group_by_session(mdrmfe)
    lrm_status = _lrm_by_fcid(lrm)
    errors = first_error_by_session(sessions, flat_errors)

    universe: dict[str, str] = {}
    for s in sessions:
        if s.session_id:
            universe.setdefault(s.session_id, SOURCE_MERGE)
    for session_id in by_session:
        universe.setdefault(session_id, SOURCE_DRM_ONLY)

    subcategories = subcategories or {}
    counts: Counter[tuple[str, str, str, str, str, str, str]] = Counter()
    for session_id, source in universe.items():
        rows = by_session.get(session_id, [])
        code = errors.get(session_id, "")
        counts[(
            source, session_kind(session_id), drm_bucket(rows),
            license_outcome(rows, lrm_status), error_group(code), code or NO_ERROR,
            subcategories.get(session_id, "") if code in NAMED_ERRORS else "",
        )] += 1
    out = [FunnelRow(opco, date, *key[:5], n, key[5], key[6]) for key, n in sorted(counts.items())]
    return FunnelResult(out, stage_totals(out))


def stage_totals(rows: Sequence[FunnelRow]) -> dict[str, int]:
    """Funnel stage counts: sessions, DRM requested, license success, errored, plus ``drm_only``."""
    def total(pred) -> int:
        return sum(r.sessions for r in rows if pred(r))

    return {
        "sessions": total(lambda r: True),
        "drm_requested": total(lambda r: r.license_outcome != NO_REQUEST),
        "license_success": total(lambda r: r.license_outcome in (SUCCESS, RETRY_THEN_SUCCESS)),
        "license_failed": total(lambda r: r.license_outcome == FAILED),
        "errored": total(lambda r: r.error_group != NO_ERROR),
        "drm_only": total(lambda r: r.source == SOURCE_DRM_ONLY),
    }
