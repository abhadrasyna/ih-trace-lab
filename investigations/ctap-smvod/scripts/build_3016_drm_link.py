"""Join 3014/3015/3016 events to mDRM household/device/CDM details (pure logic, no file or network I/O)."""
from __future__ import annotations

from lib.drm_exports import CdmRow, LrmRow, MdrmfeRow

JOINED = "joined"
NO_LICENSE_REQUEST = "no_license_request"
NO_CDM_ROW = "no_cdm_row"

DRM_COLUMNS = [
    "household_id", "device_id", "fcid", "drm_type", "br_ref", "cdm_make", "cdm_model",
    "platform", "security_level", "license_status", "drm_join",
]


def _is_success(status: str) -> bool:
    return status.startswith("2")


def _pick_mdrmfe(rows: list[MdrmfeRow]) -> dict[str, MdrmfeRow]:
    """Per sessionId: latest successful row, else latest (file order stands in for time)."""
    best: dict[str, MdrmfeRow] = {}
    for row in rows:
        if not row.session_id:
            continue
        prev = best.get(row.session_id)
        if prev is None or _is_success(row.status_code) or not _is_success(prev.status_code):
            best[row.session_id] = row
    return best


def _index_cdm(rows: list[CdmRow]) -> dict[tuple[str, str], CdmRow]:
    """Index by (fcId, scheme); identical duplicates (day + hourly slices) collapse, conflicts raise."""
    index: dict[tuple[str, str], CdmRow] = {}
    for r in rows:
        if not r.fcid:
            continue
        key = (r.fcid, r.drm_type.lower())
        if key in index and index[key] != r:
            raise ValueError(f"conflicting CDM rows for fcId {r.fcid} ({r.drm_type})")
        index[key] = r
    return index


def _index_lrm(rows: list[LrmRow]) -> dict[str, LrmRow]:
    """Per fcId (one license flow, so no cross-session mixing): the last row in file order."""
    return {r.fcid: r for r in rows if r.fcid}


def link(events: list[dict], mdrmfe: list[MdrmfeRow], cdm: list[CdmRow], lrm: list[LrmRow]) -> list[dict]:
    """Return one output row per event (same order and count) with the DRM columns added.

    ``drm_join`` is exactly one of ``joined``, ``no_license_request`` or ``no_cdm_row``.
    """
    by_session = _pick_mdrmfe(mdrmfe)
    cdm_index = _index_cdm(cdm)
    lrm_index = _index_lrm(lrm)
    clash = {c for e in events for c in DRM_COLUMNS if c in e}
    if clash:
        raise ValueError(f"events already contain DRM column(s) {sorted(clash)}; refusing to overwrite")
    out: list[dict] = []
    for event in events:
        row = {**event, **{c: "" for c in DRM_COLUMNS}}
        fe = by_session.get(event.get("sessionId") or "")
        if fe is None:
            row["drm_join"] = NO_LICENSE_REQUEST
            out.append(row)
            continue
        row.update(household_id=fe.household_id, device_id=fe.device_id, fcid=fe.fcid,
                   drm_type=fe.drm_type, br_ref=fe.br_ref)
        lic = lrm_index.get(fe.fcid)
        if lic is not None:
            row["license_status"] = lic.status_code
        cdm_row = cdm_index.get((fe.fcid, fe.drm_type.lower())) if fe.fcid else None
        if cdm_row is None:
            row["drm_join"] = NO_CDM_ROW
        else:
            row.update(cdm_make=cdm_row.make, cdm_model=cdm_row.model, platform=cdm_row.platform,
                       security_level=cdm_row.security_level, drm_join=JOINED)
        out.append(row)
    return out
