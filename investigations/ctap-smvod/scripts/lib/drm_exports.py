"""Readers for the hand-exported Lightstep mDRM CSVs (see docs/lightstep-drm-exports.md)."""
from __future__ import annotations

import csv
import json
import warnings
from dataclasses import dataclass
from pathlib import Path

MDRMFE = "mdrmfe"
WIDEVINE = "mdrm-cdm-widevine"
PLAYREADY = "mdrm-cdm-playready"
FAIRPLAY = "mdrm-cdm-fairplay"
LRM = "mdrm-lrm"

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    MDRMFE: (
        "drmAuthToken.sessionId", "fcid", "drmAuthToken.householdId", "drmAuthToken.deviceId",
        "drmAuthToken.brRef", "drmAuthToken.drmType", "http.status_code",
    ),
    WIDEVINE: ("fcId", "drmInfo.Make", "drmInfo.Model", "drmInfo.Platform", "drmInfo.SecurityLevel"),
    PLAYREADY: ("fcId", "drmInfo.manufacturerName", "drmInfo.modelName"),
    FAIRPLAY: ("fcId", "FP_SPC_contents"),
    LRM: ("fcId", "deviceId", "http.status_code"),
}


@dataclass(frozen=True)
class MdrmfeRow:
    session_id: str
    fcid: str
    household_id: str
    device_id: str
    br_ref: str
    drm_type: str
    status_code: str


@dataclass(frozen=True)
class CdmRow:
    fcid: str
    drm_type: str
    make: str
    model: str
    platform: str
    security_level: str


@dataclass(frozen=True)
class LrmRow:
    fcid: str
    device_id: str
    status_code: str


@dataclass(frozen=True)
class FairplayDevice:
    device_type: str
    os: str
    security_level: str
    valid: bool = True


def parse_fairplay_spc(raw: str) -> FairplayDevice:
    """Parse ``FP_SPC_contents``; invalid or unexpected JSON yields empty fields with ``valid=False``."""
    empty = FairplayDevice("", "", "", valid=False)
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return empty
    if not isinstance(data, dict):
        return empty
    parts: dict[str, str] = {}
    for item in str(data.get("DeviceInfo") or "").split(","):
        key, sep, value = item.partition(":")
        if sep:
            parts[key.strip()] = value.strip()
    return FairplayDevice(parts.get("Type", ""), parts.get("OS", ""), str(data.get("SecurityLevel") or ""))


def _read_dicts(path: Path, kind: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS[kind] if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing required column(s) {missing}")
        return list(reader)


def export_paths(directory: Path, date: str, kind: str) -> list[Path]:
    """Day file ``<date>_<kind>.csv`` plus hourly slices ``<date>_NN_<kind>.csv``, when present."""
    day = directory / f"{date}_{kind}.csv"
    paths = [day] if day.exists() else []
    paths.extend(sorted(directory.glob(f"{date}_[0-9][0-9]_{kind}.csv")))
    return paths


def _read_kind(directory: Path, date: str, kind: str) -> list[dict[str, str]]:
    paths = export_paths(directory, date, kind)
    if not paths:
        raise FileNotFoundError(f"no {kind} export for {date} in {directory}")
    return [row for path in paths for row in _read_dicts(path, kind)]


def _s(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def read_mdrmfe(directory: Path, date: str) -> list[MdrmfeRow]:
    return [
        MdrmfeRow(
            _s(r, "drmAuthToken.sessionId"), _s(r, "fcid"), _s(r, "drmAuthToken.householdId"),
            _s(r, "drmAuthToken.deviceId"), _s(r, "drmAuthToken.brRef"), _s(r, "drmAuthToken.drmType"),
            _s(r, "http.status_code"),
        )
        for r in _read_kind(directory, date, MDRMFE)
    ]


def read_lrm(directory: Path, date: str) -> list[LrmRow]:
    return [
        LrmRow(_s(r, "fcId"), _s(r, "deviceId"), _s(r, "http.status_code"))
        for r in _read_kind(directory, date, LRM)
    ]


def read_cdm(directory: Path, date: str) -> list[CdmRow]:
    """All CDM rows across Widevine, PlayReady and FairPlay; a scheme with no export file is skipped.

    ``drm_type`` is the scheme name (``widevine``, ``playready``, ``fairplay``). At least one
    scheme file must exist.
    """
    rows: list[CdmRow] = []
    found = False
    unparsed = 0
    for kind, scheme in ((WIDEVINE, "widevine"), (PLAYREADY, "playready"), (FAIRPLAY, "fairplay")):
        if not export_paths(directory, date, kind):
            continue
        found = True
        for r in _read_kind(directory, date, kind):
            if kind == WIDEVINE:
                rows.append(CdmRow(_s(r, "fcId"), scheme, _s(r, "drmInfo.Make"), _s(r, "drmInfo.Model"),
                                   _s(r, "drmInfo.Platform"), _s(r, "drmInfo.SecurityLevel")))
            elif kind == PLAYREADY:
                rows.append(CdmRow(_s(r, "fcId"), scheme, _s(r, "drmInfo.manufacturerName"),
                                   _s(r, "drmInfo.modelName"), "", ""))
            else:
                dev = parse_fairplay_spc(r.get("FP_SPC_contents") or "")
                if not dev.valid:
                    unparsed += 1
                rows.append(CdmRow(_s(r, "fcId"), scheme, "Apple", dev.device_type, dev.os, dev.security_level))
    if not found:
        raise FileNotFoundError(f"no CDM export (widevine/playready/fairplay) for {date} in {directory}")
    if unparsed:
        warnings.warn(f"{unparsed} FairPlay row(s) for {date} had unparseable FP_SPC_contents; fields left empty")
    return rows
