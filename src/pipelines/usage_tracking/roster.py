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
    tenant: str
    track: bool
    members: tuple[Member, ...]
    phone: str | None = None


@dataclass(frozen=True)
class Roster:
    households: tuple[Household, ...]


def resolve_config_path(cli_value: str | Path | None = None) -> Path:
    """`--config` wins, then the TRACK_CONFIG environment variable, then the repo default."""
    if cli_value:
        return Path(cli_value)
    return Path(os.environ[CONFIG_ENV_VAR]) if os.environ.get(CONFIG_ENV_VAR) else DEFAULT_CONFIG


def load(path: Path, registry: TenantRegistry | None = None) -> Roster:
    data = _read(path)
    registry = registry or TenantRegistry()
    entries = data.get("households")
    if not isinstance(entries, list) or not entries:
        raise RosterError(f"{path}: 'households' must be a non-empty list")
    households = tuple(_household(entry, registry) for entry in entries)
    _reject_duplicate_hhids(households)
    _reject_duplicate_devices(households)
    return Roster(households=households)


def tracked(roster: Roster) -> list[Household]:
    return [household for household in roster.households if household.track]


def by_tenant(roster: Roster) -> dict[str, list[Household]]:
    """Tracked households grouped by tenant code, in roster order, so each source queries one tenant at a time."""
    grouped: dict[str, list[Household]] = {}
    for household in tracked(roster):
        grouped.setdefault(household.tenant, []).append(household)
    return grouped


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
        raise RosterError(f"{path}: top level must be a mapping with 'households'")
    return data


def _tenant(hhid: str, code: Any, registry: TenantRegistry) -> str:
    if not isinstance(code, str) or not code.strip():
        raise RosterError(f"household {hhid}: missing 'tenant'")
    try:
        return registry.get(code.strip()).code
    except KeyError as exc:
        raise RosterError(f"household {hhid}: unknown tenant {code!r}: {exc.args[0]}") from exc


def _household(entry: Any, registry: TenantRegistry) -> Household:
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
    phone = _phone(hhid, entry.get("phone"), track)
    return Household(
        hhid=hhid.strip(),
        label=str(entry.get("label") or hhid),
        tenant=_tenant(hhid, entry.get("tenant"), registry),
        track=track,
        members=tuple(_member(hhid, member) for member in members),
        phone=phone,
    )


def _phone(hhid: str, value: Any, track: bool) -> str | None:
    if value is None:
        if track:
            raise RosterError(f"household {hhid}: a tracked household needs a phone")
        return None
    # A quoted string is required: unquoted digits parse as an int in YAML and lose any leading zero.
    if not isinstance(value, str) or not value.strip():
        raise RosterError(f"household {hhid}: 'phone' must be a non-empty quoted string, got {value!r}")
    return value.strip()


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
    seen: set[tuple[str, str]] = set()
    for household in households:
        key = (household.tenant, household.hhid)
        if key in seen:
            raise RosterError(f"duplicate hhid {household.hhid} in tenant {household.tenant}")
        seen.add(key)


def _reject_duplicate_devices(households: tuple[Household, ...]) -> None:
    seen: dict[tuple[str, str], str] = {}
    for household in households:
        for member in household.members:
            key = (household.tenant, member.device_id)
            if key in seen:
                raise RosterError(
                    f"duplicate device_id {member.device_id} in tenant {household.tenant} ({member.name} in {household.hhid}; first seen in {seen[key]})"
                )
            seen[key] = household.hhid
