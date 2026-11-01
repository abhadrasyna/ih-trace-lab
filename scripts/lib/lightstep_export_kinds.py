"""Per-kind registry for the Lightstep daily exports: template, tenant system, output suffix, columns.

The registry is plain data (``KINDS``); a ninth kind is one new entry. Project, region and tenant values come
from ``src.tenant_registry`` (``config/tenants.yaml``) and are never hardcoded here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.tenant_registry import LightstepGoQueryTarget, LightstepMdrmQueryTarget, QueryTarget, TenantConfig

QUERIES_DIR = Path(__file__).resolve().parents[2] / "queries" / "lightstep"
STAT_COLUMNS = ("min", "max", "avg", "sum", "value")

GO = "lightstep_go"
MDRM = "lightstep_mdrm"
ALWAYS = "always"
SHARED_ONLY = "shared_only"
NONE = "none"
_PLACEHOLDER = re.compile(r"\{\{\w+\}\}")


class UnknownKindError(KeyError):
    """Raised for a kind that is not in the registry."""


class TemplateError(ValueError):
    """Raised when a template file is missing its query block or an expansion leaves placeholders."""


@dataclass(frozen=True)
class KindSpec:
    """One export kind.

    ``tenant_scope`` says when the tenant clause applies (``always``, ``shared_only`` or ``none``);
    ``tenant_attribute`` is the span attribute it filters on and ``tenant_value`` the ``TenantConfig`` field
    holding the value. ``derived_from`` marks a kind built from another kind's query (``smvod-ts``), in which
    case ``placeholder_columns`` are written empty.
    """

    kind: str
    template_slug: str
    system: str
    suffix: str
    columns: tuple[str, ...]
    tenant_attribute: str | None = None
    tenant_scope: str = NONE
    tenant_value: str = "go_id"
    derived_from: str | None = None
    placeholder_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExportTarget:
    """Concrete project, region and the tenant fragments substituted into the template."""

    project: str
    region: str
    tenant_filter: str
    tenant_group_by: str


_SMVOD_COLUMNS = (
    "householdId", "deviceId", "session.clientIp", "sessionId", "contentId", "externalPackageId",
    "lightstep.trace_id", "playbackURL",
)
_SMVOD_TS_PLACEHOLDERS = ("error_flag", "component_name", "span_name", "duration_millis")

KINDS: dict[str, KindSpec] = {
    spec.kind: spec
    for spec in (
        KindSpec("ctap", "lightstep-export-ctap", GO, "ctap", ("http.user_agent", "lightstep.trace_id"),
                 "sessionInfo.busUnitId", SHARED_ONLY),
        KindSpec("smvod", "lightstep-export-smvod", GO, "smvod", _SMVOD_COLUMNS, "busUnitId", SHARED_ONLY),
        KindSpec(
            "smvod-ts", "lightstep-export-smvod", GO, "smvod-ts",
            (*_SMVOD_TS_PLACEHOLDERS, *_SMVOD_COLUMNS, "oldest_micros", "youngest_micros"),
            "busUnitId", SHARED_ONLY, derived_from="smvod", placeholder_columns=_SMVOD_TS_PLACEHOLDERS,
        ),
        KindSpec(
            "mdrmfe", "lightstep-export-mdrmfe", GO, "mdrmfe",
            ("drmAuthToken.sessionId", "fcid", "drmAuthToken.householdId", "drmAuthToken.deviceId",
             "drmAuthToken.deviceType", "drmAuthToken.drmType", "drmAuthToken.brRef", "request.contentId",
             "http.status_code", "http.user_agent", "http.client_ip"),
            "request.tenant", ALWAYS,
        ),
        KindSpec(
            "mdrm-cdm-widevine", "lightstep-export-mdrm-cdm-widevine", MDRM, "mdrm-cdm-widevine",
            ("fcId", "http.status_code", "drmInfo.DeviceType", "drmInfo.Make", "drmInfo.Model",
             "drmInfo.Platform", "drmInfo.SecurityLevel"),
            "tenantId", ALWAYS, "mdrm_tenant_id",
        ),
        KindSpec("mdrm-cdm-fairplay", "lightstep-export-mdrm-cdm-fairplay", MDRM, "mdrm-cdm-fairplay",
                 ("fcId", "http.status_code", "FP_SPC_contents"), "tenantId", ALWAYS, "mdrm_tenant_id"),
        KindSpec(
            "mdrm-cdm-playready", "lightstep-export-mdrm-cdm-playready", MDRM, "mdrm-cdm-playready",
            ("fcId", "http.status_code", "drmInfo.deviceType", "drmInfo.manufacturerName", "drmInfo.modelName"),
            "tenantId", ALWAYS, "mdrm_tenant_id",
        ),
        KindSpec("mdrm-lrm", "lightstep-export-mdrm-lrm", MDRM, "mdrm-lrm",
                 ("fcId", "deviceId", "http.status_code"), "tenantId", ALWAYS, "mdrm_tenant_id"),
    )
}

_TARGETS: dict[str, QueryTarget] = {GO: LightstepGoQueryTarget(), MDRM: LightstepMdrmQueryTarget()}


def get_kind(kind: str) -> KindSpec:
    """Return the registry entry for ``kind``; raise ``UnknownKindError`` if it is not registered."""

    try:
        return KINDS[kind]
    except KeyError:
        raise UnknownKindError(f"Unknown export kind '{kind}'. Known kinds: {', '.join(KINDS)}") from None


def output_file_name(kind: str, date: str) -> str:
    """Return ``<date>_<suffix>.csv`` for ``kind`` (``date`` as ``YYYY-MM-DD``)."""

    return f"{date}_{get_kind(kind).suffix}.csv"


def _tenant_applies(spec: KindSpec, tenant: TenantConfig) -> bool:
    return spec.tenant_scope == ALWAYS or (spec.tenant_scope == SHARED_ONLY and tenant.shared_project)


def expected_columns(kind: str, tenant: TenantConfig) -> tuple[str, ...]:
    """Return the CSV header columns for ``kind`` and ``tenant`` (tenant column only when applicable)."""

    spec = get_kind(kind)
    columns = list(spec.columns)
    if spec.tenant_scope == SHARED_ONLY and tenant.shared_project and spec.tenant_attribute:
        position = columns.index("oldest_micros") if spec.derived_from else len(columns)
        columns.insert(position, spec.tenant_attribute)
    if spec.derived_from:
        return tuple(columns)
    return (*columns, *STAT_COLUMNS)


def resolve_target(kind: str, tenant: TenantConfig) -> ExportTarget:
    """Resolve project, region and tenant fragments for ``kind`` through the tenant-registry query targets."""

    spec = get_kind(kind)
    context = _TARGETS[spec.system].build_context(tenant)
    tenant_filter = tenant_group_by = ""
    if _tenant_applies(spec, tenant):
        value = getattr(tenant, spec.tenant_value)
        if not value or not spec.tenant_attribute:
            raise ValueError(f"Tenant '{tenant.code}' has no {spec.tenant_value} for kind '{kind}'.")
        attribute = spec.tenant_attribute
        tenant_filter = f' && "{attribute}" == "{value}"' if attribute == "tenantId" else f' && {attribute} == "{value}"'
        if spec.tenant_scope == SHARED_ONLY:
            tenant_group_by = f', "{attribute}"'
    return ExportTarget(str(context["project"]), str(context["region"]), tenant_filter, tenant_group_by)


def load_template(kind: str, queries_dir: Path = QUERIES_DIR) -> str:
    """Return the first fenced query block of the kind's template file."""

    path = queries_dir / f"{get_kind(kind).template_slug}.md"
    match = re.search(r"```\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL)
    if match is None:
        raise TemplateError(f"{path.name}: no fenced query block found")
    return match.group(1)


def expand_query(kind: str, tenant: TenantConfig, queries_dir: Path = QUERIES_DIR) -> str:
    """Return the UQL for ``kind`` and ``tenant`` with all placeholders filled."""

    target = resolve_target(kind, tenant)
    query = load_template(kind, queries_dir)
    query = query.replace("{{tenant_filter}}", target.tenant_filter)
    query = query.replace("{{tenant_group_by}}", target.tenant_group_by)
    leftover = _PLACEHOLDER.findall(query)
    if leftover:
        raise TemplateError(f"Unfilled placeholder(s) {leftover} in template for kind '{kind}'")
    return query
