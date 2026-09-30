"""System-specific query target builders."""

from __future__ import annotations

from typing import Protocol

from .models import TenantConfig


class QueryTarget(Protocol):
    """Build the system-specific query context for one tenant."""

    def build_context(self, tenant: TenantConfig) -> dict[str, object]:
        """Return the concrete query context for ``tenant``."""


class LightstepGoQueryTarget:
    """Build Lightstep project/filter context."""

    def build_context(self, tenant: TenantConfig) -> dict[str, object]:
        if tenant.shared_project and not tenant.go_id:
            raise ValueError("Shared-project Lightstep queries require a tenant go_id for busUnitId filtering.")
        filter_value = None
        if tenant.shared_project:
            filter_value = {tenant.disambiguation_attribute or "sessionInfo.busUnitId": tenant.go_id}
        return {
            "project": tenant.lightstep_project,
            "region": tenant.lightstep_region,
            "filter": filter_value,
        }


class MatisseQueryTarget:
    """Build Matisse project/client-tenant context."""

    def build_context(self, tenant: TenantConfig) -> dict[str, object]:
        return {
            "project_id": tenant.matisse_project_id,
            "client_tenant_id": tenant.matisse_client_tenant_id,
        }


class AthenaQueryTarget:
    """Build Athena database/profile/region context."""

    def build_context(self, tenant: TenantConfig) -> dict[str, object]:
        return {
            "database": f"unified_{tenant.athena_tenant_id}",
            "profile": tenant.athena_profile,
            "region": tenant.athena_region,
        }
