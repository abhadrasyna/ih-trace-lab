"""Tests for tenant context resolution and input discovery."""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import load_script

tenant_context = load_script("lib/tenant_context.py")


def test_context_values_come_from_registry() -> None:
    zm = tenant_context.resolve_tenant_context("ZM")
    sa = tenant_context.resolve_tenant_context("SA")

    assert (zm.athena_tenant_id, zm.database, zm.debug_events_table) == ("a7vli5h8", "unified_a7vli5h8", "a7vli5h8_ccl_debug_events")
    assert (zm.profile, zm.region, zm.lightstep_project) == ("clarissa-insights-product", "eu-central-1", "mcs-go-prod-mtn-1-eu")
    assert (zm.disambiguation_attribute, zm.disambiguation_value) == ("sessionInfo.busUnitId", "dtunf6yo")
    assert sa.database == "unified_e6auj7k7"
    assert (sa.disambiguation_attribute, sa.disambiguation_value) == (None, None)


def test_unknown_tenant_fails_with_expected_path() -> None:
    with pytest.raises(ValueError, match=r"Unknown tenant 'XX'.*data/lightstep/XX"):
        tenant_context.resolve_tenant_context("XX")


def test_missing_input_folder_names_expected_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=str(tmp_path / "ZM")):
        tenant_context.require_lightstep_dir("ZM", tmp_path)


def test_discovery_finds_only_tenants_with_date_files(tmp_path: Path) -> None:
    (tmp_path / "ZM").mkdir()
    (tmp_path / "ZM" / "2026-10-02_ctap.csv").write_text("a\n", encoding="utf-8")
    (tmp_path / "SA").mkdir()
    (tmp_path / "SA" / "2026-10-01_ctap.csv").write_text("a\n", encoding="utf-8")
    (tmp_path / "NG").mkdir()
    (tmp_path / "2026-10-02_ctap.csv").write_text("a\n", encoding="utf-8")

    assert tenant_context.discover_tenants("2026-10-02", data_root=tmp_path) == ["ZM"]
    assert tenant_context.discover_tenants("2026-10-03", data_root=tmp_path) == []


def test_discovery_rejects_unregistered_folder(tmp_path: Path) -> None:
    (tmp_path / "QQ").mkdir()

    with pytest.raises(ValueError, match="not a registered tenant code"):
        tenant_context.discover_tenants("2026-10-02", data_root=tmp_path)


def test_discovery_rejects_non_code_folder_name(tmp_path: Path) -> None:
    (tmp_path / "dtunf6yo").mkdir()

    with pytest.raises(ValueError, match="must be named by tenant code 'ZM'"):
        tenant_context.discover_tenants("2026-10-02", data_root=tmp_path)
