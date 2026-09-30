"""Tests for src/tenant_registry/registry.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tenant_registry.registry import TenantRegistry

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "tenants_test.yaml"


def test_get_by_each_id_type_returns_correct_tenant() -> None:
    registry = TenantRegistry(FIXTURE_PATH)

    identifiers = ("iye9omdf", "1z5vo5g2", "rxviifsu", "e6auj7k7", "SA")

    for identifier in identifiers:
        tenant = registry.get(identifier)
        assert tenant.code == "SA"
        assert tenant.name == "South Africa"


def test_get_unknown_identifier_raises_key_error_listing_available_ids() -> None:
    registry = TenantRegistry(FIXTURE_PATH)

    with pytest.raises(KeyError, match="Unknown tenant 'missing'. Available tenant ids: iye9omdf, apbyfj9d"):
        registry.get("missing")
