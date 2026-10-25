"""Pure license-chain quality checks over the mDRM exports (mdrmfe -> LRM / CDM, joined on ``fcId``).

No file or network I/O; ``analyze_mdrm_quality.py`` feeds in rows read by ``lib.drm_exports``. The CDM
exports carry no ``deviceId`` or ``sessionId``, so a device mismatch is only checked mdrmfe against LRM.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from lib.drm_exports import CdmRow, LrmRow, MdrmfeRow
from lib.drm_funnel import LRM_OK, MDRMFE_OK

UNKNOWN = "unknown"
EXPORT_MDRMFE, EXPORT_LRM, EXPORT_CDM = "mdrmfe", "lrm", "cdm"


@dataclass(frozen=True)
class StatusCount:
    export: str
    drm_type: str
    status: str
    count: int


@dataclass(frozen=True)
class FailedRequest:
    """One failing ``fcId``; ``layers`` is ``mdrmfe``, ``lrm`` or ``mdrmfe+lrm``."""

    fcid: str
    layers: str
    mdrmfe_status: str
    lrm_status: str
    session_id: str
    household_id: str
    device_id: str
    content_id: str
    user_agent: str
    drm_type: str


@dataclass(frozen=True)
class FcidChain:
    """Set differences between the exports, plus mdrmfe/LRM ``deviceId`` disagreements."""

    mdrmfe_total: int
    lrm_total: int
    cdm_total: int
    mdrmfe_not_in_lrm: int
    mdrmfe_not_in_lrm_ok: int
    mdrmfe_not_in_cdm: int
    lrm_not_in_mdrmfe: int
    cdm_not_in_mdrmfe: int
    device_mismatches: list[tuple[str, str, str]]


def _mdrmfe_type_by_fcid(mdrmfe: Sequence[MdrmfeRow]) -> dict[str, str]:
    types: dict[str, str] = {}
    for r in mdrmfe:
        if r.fcid:
            types.setdefault(r.fcid, r.drm_type.lower() or UNKNOWN)
    return types


def status_counts(
    mdrmfe: Sequence[MdrmfeRow], lrm: Sequence[LrmRow], cdm: Sequence[CdmRow]
) -> list[StatusCount]:
    """Rows per export, DRM type and HTTP status. LRM has no DRM type, so it takes the mdrmfe type by ``fcId``."""
    type_by_fcid = _mdrmfe_type_by_fcid(mdrmfe)
    counts: Counter[tuple[str, str, str]] = Counter()
    for r in mdrmfe:
        counts[(EXPORT_MDRMFE, r.drm_type.lower() or UNKNOWN, r.status_code or UNKNOWN)] += 1
    for r in lrm:
        counts[(EXPORT_LRM, type_by_fcid.get(r.fcid, UNKNOWN), r.status_code or UNKNOWN)] += 1
    for r in cdm:
        counts[(EXPORT_CDM, r.drm_type, r.status_code or UNKNOWN)] += 1
    return [StatusCount(*key, n) for key, n in sorted(counts.items())]


def _lrm_by_fcid(lrm: Sequence[LrmRow]) -> dict[str, list[LrmRow]]:
    grouped: dict[str, list[LrmRow]] = defaultdict(list)
    for r in lrm:
        if r.fcid:
            grouped[r.fcid].append(r)
    return grouped


def failing_requests(mdrmfe: Sequence[MdrmfeRow], lrm: Sequence[LrmRow]) -> list[FailedRequest]:
    """Distinct failing ``fcId``s: mdrmfe not 201 or any LRM row not 200, with the layers that failed."""
    lrm_rows = _lrm_by_fcid(lrm)
    failed: dict[str, FailedRequest] = {}
    for r in mdrmfe:
        if r.fcid and r.status_code != MDRMFE_OK and r.fcid not in failed:
            bad = next((x.status_code for x in lrm_rows.get(r.fcid, []) if x.status_code != LRM_OK), "")
            failed[r.fcid] = FailedRequest(
                r.fcid, "mdrmfe+lrm" if bad else "mdrmfe", r.status_code, bad, r.session_id, r.household_id,
                r.device_id, r.content_id, r.user_agent, r.drm_type.lower() or UNKNOWN,
            )
    by_fcid = {r.fcid: r for r in mdrmfe if r.fcid}
    for fcid, rows in lrm_rows.items():
        bad = next((x for x in rows if x.status_code != LRM_OK), None)
        if bad is None or fcid in failed:
            continue
        fe = by_fcid.get(fcid)
        failed[fcid] = FailedRequest(
            fcid, "lrm", fe.status_code if fe else "", bad.status_code, fe.session_id if fe else "",
            fe.household_id if fe else "", (fe.device_id if fe else "") or bad.device_id,
            fe.content_id if fe else "", fe.user_agent if fe else "", fe.drm_type.lower() if fe else UNKNOWN,
        )
    return sorted(failed.values(), key=lambda f: f.fcid)


def layer_overlap(failures: Sequence[FailedRequest]) -> dict[str, int]:
    """Failing ``fcId``s by layer: only mdrmfe, only LRM, or both."""
    counts = Counter(f.layers for f in failures)
    return {"mdrmfe+lrm": counts["mdrmfe+lrm"], "mdrmfe": counts["mdrmfe"], "lrm": counts["lrm"]}


def repeat_failures(failures: Sequence[FailedRequest]) -> dict[str, list[tuple[str, int]]]:
    """Device, household and session ids that appear in more than one failing ``fcId``, most repeated first."""
    out: dict[str, list[tuple[str, int]]] = {}
    for dim in ("device_id", "household_id", "session_id"):
        counts = Counter(getattr(f, dim) for f in failures if getattr(f, dim))
        out[dim] = sorted(((k, n) for k, n in counts.items() if n > 1), key=lambda kv: (-kv[1], kv[0]))
    return out


def requests_per_key(mdrmfe: Sequence[MdrmfeRow], key: str) -> dict[int, int]:
    """Histogram of distinct ``fcId`` count per ``session_id`` or ``household_id`` (requests -> keys)."""
    fcids: dict[str, set[str]] = defaultdict(set)
    for r in mdrmfe:
        value = getattr(r, key)
        if value and r.fcid:
            fcids[value].add(r.fcid)
    return dict(sorted(Counter(len(v) for v in fcids.values()).items()))


def retry_sessions(mdrmfe: Sequence[MdrmfeRow]) -> list[str]:
    """Sessions with more than one distinct license request (retries or re-acquisitions)."""
    fcids: dict[str, set[str]] = defaultdict(set)
    for r in mdrmfe:
        if r.session_id and r.fcid:
            fcids[r.session_id].add(r.fcid)
    return sorted(s for s, v in fcids.items() if len(v) > 1)


def fcid_chain(mdrmfe: Sequence[MdrmfeRow], lrm: Sequence[LrmRow], cdm: Sequence[CdmRow]) -> FcidChain:
    fe = {r.fcid for r in mdrmfe if r.fcid}
    lr = {r.fcid for r in lrm if r.fcid}
    cd = {r.fcid for r in cdm if r.fcid}
    ok_fe = {r.fcid for r in mdrmfe if r.fcid and r.status_code == MDRMFE_OK}
    device_by_fcid = {r.fcid: r.device_id for r in mdrmfe if r.fcid and r.device_id}
    mismatches = sorted(
        {(r.fcid, device_by_fcid[r.fcid], r.device_id) for r in lrm
         if r.fcid in device_by_fcid and r.device_id and r.device_id != device_by_fcid[r.fcid]}
    )
    return FcidChain(len(fe), len(lr), len(cd), len(fe - lr), len((fe - lr) & ok_fe), len(fe - cd),
                     len(lr - fe), len(cd - fe), mismatches)


def duplicate_fcids_across_parts(parts: Mapping[str, Sequence[str]]) -> dict[str, list[str]]:
    """``fcId``s present in two or more files (whole-day file or ``_NN_`` parts), with the file names."""
    seen: dict[str, set[str]] = defaultdict(set)
    for name, fcids in parts.items():
        for fcid in fcids:
            if fcid:
                seen[fcid].add(name)
    return {f: sorted(names) for f, names in sorted(seen.items()) if len(names) > 1}


def whole_day_with_parts(file_names: Sequence[str], date: str, kind: str) -> str:
    """Warning text when ``<date>_<kind>.csv`` coexists with ``<date>_NN_<kind>.csv`` parts, else ``""``.

    ``export_paths`` reads both with no dedup, so every request would be counted twice.
    """
    part = re.compile(rf"^{re.escape(date)}_\d{{2}}_{re.escape(kind)}\.csv$")
    parts = [n for n in file_names if part.match(n)]
    if f"{date}_{kind}.csv" in file_names and parts:
        return f"{date}_{kind}.csv coexists with {len(parts)} part file(s); rows may be double counted"
    return ""
