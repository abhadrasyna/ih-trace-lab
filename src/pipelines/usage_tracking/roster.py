"""Load and validate the tracked-household roster (YAML, or JSON through the same loader)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.tenant_registry.registry import TenantRegistry

from .errors import RosterError

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "config" / "tracked_households.yaml"
CONFIG_ENV_VAR = "TRACK_CONFIG"


@dataclass(frozen=True)
class Member:
    name: str
    device_id: str
    active_from: str | None = None


@dataclass(frozen=True)
class Household:
    hhid: str
    label: str
    track: bool
    members: tuple[Member, ...]


@dataclass(frozen=True)
class Roster:
    tenant: str
    households: tuple[Household, ...]


def resolve_config_path(cli_value: str | Path | None = None) -> Path:
    """`--config` wins, then the TRACK_CONFIG environment variable, then the repo default."""
    if cli_value:
        return Path(cli_value)
    return Path(os.environ[CONFIG_ENV_VAR]) if os.environ.get(CONFIG_ENV_VAR) else DEFAULT_CONFIG


def load(path: Path, registry: TenantRegistry | None = None) -> Roster:
    data = _read(path)
    tenant = _tenant(data, registry or TenantRegistry())
    entries = data.get("households")
    if not isinstance(entries, list) or not entries:
        raise RosterError(f"{path}: 'households' must be a non-empty list")
    households = tuple(_household(entry) for entry in entries)
    _reject_duplicate_hhids(households)
    _reject_duplicate_devices(households)
    return Roster(tenant=tenant, households=households)


def tracked(roster: Roster) -> list[Household]:
    return [household for household in roster.households if household.track]


def _read(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RosterError(f"cannot read roster {path}: {exc}") from exc
    try:
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    except (ValueError, yaml.YAMLError) as exc:
        raise RosterError(f"{path}: not valid {'JSON' if path.suffix == '.json' else 'YAML'}: {exc}") from exc
    if not isinstance(data, dict):
        raise RosterError(f"{path}: top level must be a mapping with 'tenant' and 'households'")
    return data


def _tenant(data: dict[str, Any], registry: TenantRegistry) -> str:
    code = data.get("tenant")
    if not isinstance(code, str) or not code:
        raise RosterError("roster is missing 'tenant'")
    try:
        return registry.get(code).code
    except KeyError as exc:
        raise RosterError(f"unknown tenant {code!r}: {exc.args[0]}") from exc


def _household(entry: Any) -> Household:
    if not isinstance(entry, dict):
        raise RosterError(f"household entry must be a mapping, got {entry!r}")
    hhid = entry.get("hhid")
    if not isinstance(hhid, str) or not hhid.strip():
        raise RosterError(f"household entry has an empty or missing hhid: {entry!r}")
    track = entry.get("track")
    if not isinstance(track, bool):
        raise RosterError(f"household {hhid}: 'track' must be true or false, got {track!r}")
    members = entry.get("members")
    members = [] if members is None else members
    if not isinstance(members, list):
        raise RosterError(f"household {hhid}: 'members' must be a list")
    if track and not members:
        raise RosterError(f"household {hhid}: a tracked household needs at least one member")
    return Household(
        hhid=hhid.strip(),
        label=str(entry.get("label") or hhid),
        track=track,
        members=tuple(_member(hhid, member) for member in members),
    )


def _member(hhid: str, entry: Any) -> Member:
    if not isinstance(entry, dict):
        raise RosterError(f"household {hhid}: member must be a mapping, got {entry!r}")
    device_id = entry.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        raise RosterError(f"household {hhid}: member without a device_id: {entry!r}")
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RosterError(f"household {hhid}: member {device_id} has no name")
    return Member(name=name.strip(), device_id=device_id.strip(), active_from=_active_from(hhid, device_id, entry.get("active_from")))


def _active_from(hhid: str, device_id: str, value: Any) -> str | None:
    if value is None:
        return None
    try:
        # YAML parses an unquoted 2026-11-04 to a date; a string must be ISO YYYY-MM-DD.
        return value.isoformat() if type(value) is date else date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise RosterError(f"household {hhid}: member {device_id} has an invalid active_from {value!r} (want YYYY-MM-DD)") from exc


def _reject_duplicate_hhids(households: tuple[Household, ...]) -> None:
    seen: set[str] = set()
    for household in households:
        if household.hhid in seen:
            raise RosterError(f"duplicate hhid {household.hhid}")
        seen.add(household.hhid)


def _reject_duplicate_devices(households: tuple[Household, ...]) -> None:
    seen: dict[str, str] = {}
    for household in households:
        for member in household.members:
            if member.device_id in seen:
                raise RosterError(
                    f"duplicate device_id {member.device_id} ({member.name} in {household.hhid}; first seen in {seen[member.device_id]})"
                )
            seen[member.device_id] = household.hhid
