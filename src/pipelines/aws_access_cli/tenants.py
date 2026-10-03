"""Tenant configuration for the aws-access-cli pipeline."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    code: str
    country: str
    database: str
    debug_events_table: str

    @classmethod
    def from_tenant_id(cls, tenant_id: str, code: str, country: str) -> "TenantConfig":
        return cls(
            tenant_id=tenant_id,
            code=code,
            country=country,
            database=f"unified_{tenant_id}",
            debug_events_table=f"{tenant_id}_ccl_debug_events",
        )


DEFAULT_TENANT = TenantConfig.from_tenant_id("e6auj7k7", "ZA", "South Africa")
TENANTS_BY_CODE = {
    tenant.code: tenant
    for tenant in (
        DEFAULT_TENANT,
        TenantConfig.from_tenant_id("a7vli5h8", "ZM", "Zambia"),
        TenantConfig.from_tenant_id("is1aldzq", "GH", "Ghana"),
        TenantConfig.from_tenant_id("jsxgloje", "NG", "Nigeria"),
    )
}


def get_tenant(code: str | None) -> TenantConfig:
    if code is None:
        return DEFAULT_TENANT
    try:
        return TENANTS_BY_CODE[code]
    except KeyError as exc:
        raise KeyError(f"Unknown tenant code {code!r}; expected one of {sorted(TENANTS_BY_CODE)}") from exc


def all_tenants() -> list[TenantConfig]:
    return list(TENANTS_BY_CODE.values())
