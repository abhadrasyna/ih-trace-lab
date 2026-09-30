"""Tenant registry loader and lookup helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.tenant_registry.models import TenantConfig


class TenantRegistry:
    """Load tenant configs from YAML and resolve them by any known identifier."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or Path(__file__).resolve().parents[2] / "config" / "tenants.yaml"
        self._tenants = self._load_tenants(self._config_path)
        self._by_go_id = self._build_index("go_id")
        self._by_matisse_project_id = self._build_index("matisse_project_id")
        self._by_matisse_client_tenant_id = self._build_index("matisse_client_tenant_id")
        self._by_athena_tenant_id = self._build_index("athena_tenant_id")
        self._by_code = self._build_index("code")

    def get(self, identifier: str) -> TenantConfig:
        """Return the tenant matching ``identifier`` across all supported indexes."""

        for index in (
            self._by_go_id,
            self._by_matisse_project_id,
            self._by_matisse_client_tenant_id,
            self._by_athena_tenant_id,
            self._by_code,
        ):
            tenant = index.get(identifier)
            if tenant is not None:
                return tenant

        available = ", ".join(self.go_ids()) or "(none registered)"
        raise KeyError(f"Unknown tenant '{identifier}'. Available tenant ids: {available}")

    def go_ids(self) -> list[str]:
        """Return registered GO ids in config order."""

        return [tenant.go_id for tenant in self._tenants]

    def _build_index(self, attribute: str) -> dict[str, TenantConfig]:
        return {getattr(tenant, attribute): tenant for tenant in self._tenants}

    @staticmethod
    def _load_tenants(config_path: Path) -> list[TenantConfig]:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        opcos = payload.get("opcos", [])
        return [TenantConfig(**opco) for opco in opcos]
