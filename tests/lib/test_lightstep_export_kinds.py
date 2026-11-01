"""Offline tests for scripts/lib/lightstep_export_kinds.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib import lightstep_export_kinds as lk
from src.tenant_registry import TenantConfig

EIGHT = {
    "ctap", "smvod", "smvod-ts", "mdrmfe",
    "mdrm-cdm-widevine", "mdrm-cdm-fairplay", "mdrm-cdm-playready", "mdrm-lrm",
}


def _tenant(code: str, shared: bool, go_id: str, mdrm_id: str | None) -> TenantConfig:
    return TenantConfig(
        code=code, name=code, go_id=go_id, lightstep_project=f"proj-{code.lower()}", lightstep_region="EU",
        shared_project=shared, disambiguation_attribute="sessionInfo.busUnitId" if shared else None,
        matisse_project_id="m", matisse_client_tenant_id="c", athena_tenant_id="a", athena_profile="p",
        athena_region="r", mdrm_tenant_id=mdrm_id, mdrm_project="mdrm-proj" if mdrm_id else None,
        mdrm_region="US" if mdrm_id else None,
    )


ZA = _tenant("ZA", False, "goza", "mdza")
GH = _tenant("GH", True, "gogh", "mdgh")


def test_registry_covers_all_eight_kinds() -> None:
    assert set(lk.KINDS) == EIGHT
    for kind in EIGHT:
        spec = lk.get_kind(kind)
        assert spec.template_slug and spec.system and spec.suffix
        assert lk.load_template(kind)
    assert lk.output_file_name("smvod-ts", "2026-10-29") == "2026-10-29_smvod-ts.csv"


def test_unknown_kind_raises() -> None:
    with pytest.raises(lk.UnknownKindError):
        lk.get_kind("nope")
    with pytest.raises(lk.UnknownKindError):
        lk.output_file_name("nope", "2026-10-29")


def test_dedicated_tenant_has_no_busunitid() -> None:
    for kind in ("ctap", "smvod", "smvod-ts"):
        assert "busUnitId" not in lk.expand_query(kind, ZA)
        assert "busUnitId" not in lk.expected_columns(kind, ZA)


def test_shared_tenant_uses_kind_specific_attribute() -> None:
    ctap = lk.expand_query("ctap", GH)
    assert 'sessionInfo.busUnitId == "gogh"' in ctap and ', "sessionInfo.busUnitId"]' in ctap
    smvod = lk.expand_query("smvod", GH)
    assert ' && busUnitId == "gogh"' in smvod and "sessionInfo.busUnitId" not in smvod
    assert "busUnitId" in lk.expected_columns("smvod-ts", GH)


def test_mdrmfe_always_filters_request_tenant_with_go_id() -> None:
    assert 'request.tenant == "goza"' in lk.expand_query("mdrmfe", ZA)


def test_cdm_queries_identical_across_tenants() -> None:
    for kind in ("mdrm-cdm-widevine", "mdrm-cdm-fairplay", "mdrm-cdm-playready"):
        za = lk.expand_query(kind, ZA).replace("mdza", "<id>")
        gh = lk.expand_query(kind, GH).replace("mdgh", "<id>")
        assert za == gh and "operation ==" in za and '"tenantId" == "<id>"' in za


def test_resolve_target_without_mdrm_entry_raises() -> None:
    with pytest.raises(ValueError):
        lk.resolve_target("mdrm-lrm", _tenant("NG", False, "gong", None))
    assert lk.resolve_target("mdrm-lrm", ZA).region == "US"
    assert lk.resolve_target("ctap", ZA).project == "proj-za"


def test_expand_query_rejects_unfilled_placeholder(tmp_path: Path) -> None:
    (tmp_path / "lightstep-export-ctap.md").write_text("```\nq {{tenant_filter}} {{oops}}\n```\n")
    with pytest.raises(lk.TemplateError):
        lk.expand_query("ctap", ZA, tmp_path)
    (tmp_path / "lightstep-export-ctap.md").write_text("no block\n")
    with pytest.raises(lk.TemplateError):
        lk.load_template("ctap", tmp_path)
