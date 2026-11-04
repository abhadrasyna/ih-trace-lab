"""Concrete live clients for `--live-athena` and `--live-lightstep`: the only place that builds Athena or Lightstep clients.

Each factory takes one tenant's registry entry and returns the matching live source, built with its runner. Every failure is wrapped in the source's own error type, so `botocore` and
HTTP exceptions never leak past this module. Not unit-tested: it only wires the shared Athena adapter and Lightstep API; the sources it feeds are tested with fakes.
"""
from __future__ import annotations

from datetime import date

from scripts.lib.lightstep_api import Project, UrllibTransport, fetch_all_series, load_token, utc_day_window
from scripts.lib.lightstep_export_kinds import resolve_target
from scripts.lib.lightstep_export_runner import ENDPOINTS
from src.pipelines.aws_access_cli.runtime import RuntimeConfig, make_athena_client, make_auth
from src.tenant_registry.models import TenantConfig

from .athena_source import LiveAthenaSource
from .errors import AthenaSourceError, LightstepSourceError
from .lightstep_source import LiveLightstepSource

SERIES_POINT_SECONDS = 86400


def make_athena_source(tenant: TenantConfig, today: date) -> LiveAthenaSource:
    """Refreshes SSO once, then returns a live source that executes SQL against the tenant's Athena database."""
    try:
        make_auth().refresh_if_expired(tenant.athena_profile)
        client = make_athena_client(RuntimeConfig(profile=tenant.athena_profile, region=tenant.athena_region), f"unified_{tenant.athena_tenant_id}")
    except Exception as exc:
        raise AthenaSourceError(f"Athena auth or client setup failed for {tenant.code}: {exc}") from exc

    def run(sql: str) -> list[dict[str, str]]:
        try:
            return client.fetch_results(client.start_query(sql, {})).rows
        except Exception as exc:
            raise AthenaSourceError(f"Athena query failed for {tenant.code}: {exc}") from exc

    return LiveAthenaSource(tenant.code, tenant.athena_tenant_id, run, today)


def make_lightstep_source(tenant: TenantConfig) -> LiveLightstepSource:
    """Returns a live source that fetches the tenant's sm-vod Lightstep series for one UTC day."""
    try:
        target = resolve_target("smvod", tenant)
        base_url, org = ENDPOINTS[target.region.upper()]
        project = Project(base_url, org, target.project)
        token = load_token(target.region)
    except Exception as exc:
        raise LightstepSourceError(f"Lightstep setup failed for {tenant.code}: {exc}") from exc
    transport = UrllibTransport()

    def run(uql: str, day: date) -> list[dict[str, object]]:
        oldest, youngest = utc_day_window(str(day))
        try:
            series = fetch_all_series(transport, project=project, token=token, uql=uql, oldest=oldest, youngest=youngest, output_period=SERIES_POINT_SECONDS)
        except Exception as exc:
            raise LightstepSourceError(f"Lightstep query failed for {tenant.code}: {exc}") from exc
        return series  # type: ignore[return-value]  # Series is a TypedDict-like mapping, the source reads it as plain dicts

    return LiveLightstepSource(tenant.code, run, target.tenant_filter)
