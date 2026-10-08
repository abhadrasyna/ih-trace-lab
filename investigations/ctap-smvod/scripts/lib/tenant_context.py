"""Resolve a tenant code into the frozen context the CTAP/SM-VOD pipeline steps consume."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lib.runtime import investigation_data_dir
from src.tenant_registry import AthenaQueryTarget, TenantRegistry

LIGHTSTEP_TOOL = "lightstep"


@dataclass(frozen=True)
class TenantContext:
    code: str
    athena_tenant_id: str
    database: str
    debug_events_table: str
    profile: str
    region: str
    lightstep_project: str
    disambiguation_attribute: str | None
    disambiguation_value: str | None


def resolve_tenant_context(code: str, registry: TenantRegistry | None = None) -> TenantContext:
    """Build the context for `code` from `config/tenants.yaml`; unknown codes raise ValueError."""
    registry = registry or TenantRegistry()
    try:
        tenant = registry.get(code)
    except KeyError as exc:
        raise ValueError(f"{exc.args[0]}. Expected input folder: {lightstep_dir(code)}") from exc
    athena = AthenaQueryTarget().build_context(tenant)
    attribute = tenant.disambiguation_attribute if tenant.shared_project else None
    return TenantContext(
        code=tenant.code,
        athena_tenant_id=tenant.athena_tenant_id,
        database=str(athena["database"]),
        debug_events_table=f"{tenant.athena_tenant_id}_ccl_debug_events",
        profile=str(athena["profile"]),
        region=str(athena["region"]),
        lightstep_project=tenant.lightstep_project,
        disambiguation_attribute=attribute,
        disambiguation_value=tenant.go_id if attribute else None,
    )


def lightstep_dir(code: str, data_root: str | Path | None = None) -> Path:
    """Folder holding a tenant's Lightstep exports (`data_root` replaces `data/lightstep` for tests)."""
    if data_root is not None:
        return Path(data_root) / code
    return investigation_data_dir(LIGHTSTEP_TOOL, tenant=code)


def require_lightstep_dir(code: str, data_root: str | Path | None = None) -> Path:
    path = lightstep_dir(code, data_root)
    if not path.is_dir():
        raise FileNotFoundError(f"No Lightstep input folder for tenant {code}: expected {path}")
    return path


def discover_tenants(
    date_iso: str,
    registry: TenantRegistry | None = None,
    data_root: str | Path | None = None,
) -> list[str]:
    """Registered tenant codes whose Lightstep folder holds files for `date_iso`, sorted."""
    registry = registry or TenantRegistry()
    root = Path(data_root) if data_root is not None else investigation_data_dir(LIGHTSTEP_TOOL)
    if not root.is_dir():
        return []
    found: list[str] = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            code = registry.get(folder.name).code
        except KeyError as exc:
            raise ValueError(f"{folder} is not a registered tenant code: {exc.args[0]}") from exc
        if code != folder.name:
            raise ValueError(f"{folder} must be named by tenant code '{code}'")
        if any(folder.glob(f"{date_iso}_*.csv")):
            found.append(code)
    return found
