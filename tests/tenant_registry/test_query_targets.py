"""Tests for src/tenant_registry/query_targets.py."""

from __future__ import annotations

import dataclasses

import pytest

from src.tenant_registry.models import TenantConfig
from src.tenant_registry.query_targets import (
    AthenaQueryTarget,
    LightstepGoQueryTarget,
    MatisseQueryTarget,
)


def _tenant(**overrides: object) -> TenantConfig:
    base = TenantConfig(
        code="GH",
        name="Ghana",
        go_id="apbyfj9d",
        lightstep_project="mcs-go-prod-mtn-1-eu",
        lightstep_region="EU",
        shared_project=True,
        disambiguation_attribute="sessionInfo.busUnitId",
        matisse_project_id="0800cgn3",
        matisse_client_tenant_id="hkq8wgfy",
        athena_tenant_id="is1aldzq",
        athena_profile="clarissa-insights-product",
        athena_region="eu-central-1",
    )
    return dataclasses.replace(base, **overrides)


def test_lightstep_go_dedicated_project_has_no_filter() -> None:
    target = LightstepGoQueryTarget()

    context = target.build_context(
        _tenant(
            code="SA",
            name="South Africa",
            go_id="iye9omdf",
            lightstep_project="mcs-go-prod-iye9omdf-eu",
            shared_project=False,
            disambiguation_attribute=None,
        )
    )

    assert context == {
        "project": "mcs-go-prod-iye9omdf-eu",
        "region": "EU",
        "filter": None,
    }


def test_lightstep_go_shared_project_includes_bus_unit_id_filter() -> None:
    target = LightstepGoQueryTarget()

    context = target.build_context(_tenant())

    assert context == {
        "project": "mcs-go-prod-mtn-1-eu",
        "region": "EU",
        "filter": {"sessionInfo.busUnitId": "apbyfj9d"},
    }


def test_matisse_and_athena_build_context_happy_path() -> None:
    tenant = _tenant()

    assert MatisseQueryTarget().build_context(tenant) == {
        "project_id": "0800cgn3",
        "client_tenant_id": "hkq8wgfy",
    }
    assert AthenaQueryTarget().build_context(tenant) == {
        "database": "unified_is1aldzq",
        "profile": "clarissa-insights-product",
        "region": "eu-central-1",
    }


def test_lightstep_go_shared_project_missing_go_id_raises_value_error() -> None:
    target = LightstepGoQueryTarget()

    with pytest.raises(ValueError, match="Shared-project Lightstep queries require a tenant go_id"):
        target.build_context(_tenant(go_id=""))
