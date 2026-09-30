"""Tenant registry data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantConfig:
    """Canonical config for one onboarded tenant."""

    code: str
    name: str
    go_id: str
    lightstep_project: str
    lightstep_region: str
    shared_project: bool
    disambiguation_attribute: str | None
    matisse_project_id: str
    matisse_client_tenant_id: str
    athena_tenant_id: str
    athena_profile: str
    athena_region: str
