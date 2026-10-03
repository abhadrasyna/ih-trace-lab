"""Business logic for aws-access-cli adoption-family reports."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from src.lib.athena.protocols import AthenaClient
from src.lib.csv_io.protocols import CsvWriterProtocol
from src.lib.paths.protocols import PathResolver
from src.pipelines.aws_access_cli.catalog import QueryCatalog, quote_sql_literal
from src.pipelines.aws_access_cli.tenants import TenantConfig

_PERIOD_EXPR = {
    "day": "date(timestamp_formatted)",
    "week": "date_trunc('week', date(timestamp_formatted))",
    "month": "date_trunc('month', date(timestamp_formatted))",
}
_DEBUG_PERIOD_EXPR = {
    "day": "date(substr(datetime, 1, 10))",
    "week": "date_trunc('week', date(substr(datetime, 1, 10)))",
    "month": "date_trunc('month', date(substr(datetime, 1, 10)))",
}


@dataclass(frozen=True)
class MetricSpec:
    name: str
    column_header: str
    query_key: str
    params: Mapping[str, str]
    debug_table: bool = False


def _iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _end_exclusive(value: str) -> str:
    return (_iso_date(value) + timedelta(days=1)).isoformat()


def _merge_rows(metric_rows: Iterable[dict[str, str]], column_header: str, merged: dict[str, dict[str, str]]) -> None:
    for row in metric_rows:
        session_date = row.get("session_date", "")
        metric_value = row.get("metric_value", "")
        if not session_date:
            continue
        merged.setdefault(session_date, {"session_date": session_date})[column_header] = metric_value


def _render_metric_sql(
    catalog: QueryCatalog,
    tenant: TenantConfig,
    metric: MetricSpec,
    start_date: str,
    end_date: str,
    period: str,
    *,
    table_override: str | None = None,
) -> str:
    if period not in _PERIOD_EXPR:
        raise ValueError(f"Unsupported period {period!r}; expected one of {sorted(_PERIOD_EXPR)}")
    validated_start_date = _iso_date(start_date).isoformat()
    validated_end_date = _iso_date(end_date).isoformat()
    if validated_end_date < validated_start_date:
        raise ValueError("end_date must be on or after start_date")
    params = {
        "database": quote_sql_literal(tenant.database),
        "database_identifier": tenant.database,
        "start_date": validated_start_date,
        "end_date_exclusive": _end_exclusive(validated_end_date),
        "session_date_expr": _DEBUG_PERIOD_EXPR[period] if metric.debug_table else _PERIOD_EXPR[period],
        "table_identifier": table_override or tenant.debug_events_table,
        **metric.params,
    }
    return catalog.render(metric.query_key, params)


def _run_sql(athena: AthenaClient, sql: str) -> list[dict[str, str]]:
    execution_id = athena.start_query(sql, {})
    return athena.fetch_results(execution_id).rows


HOUSEHOLD_METRICS = (
    MetricSpec("home-unique-hhid", "Home-Screen-UnqHHID", "aws-access-cli_adoption_distinct", {"table": "fact_navigation_interactions", "distinct_expression": "user_id", "extra_where": "AND event_source = 'home'"}),
    MetricSpec("attempts-unique-hhid", "attempts-unique-hhid", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "user_id", "extra_where": "AND event_type = 'REQUEST_VIEWING'"}),
    MetricSpec("unique-hh-no-vsf", "unique-hh-no-vsf", "aws-access-cli_adoption_no_vsf", {}),
    MetricSpec("successful-vod-playback-hhid", "successful_vod_playback_hhid", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "user_id", "extra_where": "AND event_type = 'PLAY' AND endreason LIKE 'DESTROY'"}),
    MetricSpec("vsf-unique-hhid", "vsf_unique_hhid", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "user_id", "extra_where": "AND event_type = 'REQUEST_VIEWING' AND endreason LIKE 'PLAYER_ERROR'"}),
    MetricSpec("ebvs-unique-hhid", "ebvs_unique_hhid", "aws-access-cli_adoption_playback_outcome", {"distinct_expression": "user_id", "select_identity_columns": "user_id,", "group_identity_columns": "user_id,", "outcome_value": "EBVS"}),
)
SESSION_METRICS = (
    MetricSpec("vod-playback-attempt-sessions", "VOD-Playback-Attempt-Sessions", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "parent_session_id", "extra_where": "AND event_type = 'REQUEST_VIEWING'"}),
    MetricSpec("successful-vod-playback-sessions", "Successful-VOD-Playback-Sessions", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "parent_session_id", "extra_where": "AND event_type = 'PLAY' AND endreason LIKE 'DESTROY'"}),
    MetricSpec("vsf-sessions", "VSF-Sessions", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "parent_session_id", "extra_where": "AND event_type = 'REQUEST_VIEWING' AND endreason LIKE 'PLAYER_ERROR'"}),
    MetricSpec("ebvs-sessions", "EBVS-Sessions", "aws-access-cli_adoption_playback_outcome", {"distinct_expression": "parent_session_id", "select_identity_columns": "", "group_identity_columns": "", "outcome_value": "EBVS"}),
)
GUEST_METRICS = (
    MetricSpec("unique-guest-session", "unique_guest_session", "aws-access-cli_unique_guest_session", {}, debug_table=True),
    MetricSpec("guest-login-prompt-hhid", "guest_login_prompt_hhid", "aws-access-cli_adoption_distinct", {"table": "fact_navigation_interactions", "distinct_expression": "user_id", "extra_where": "AND event_source = 'guestLoginPrompt'"}),
    MetricSpec("guest-login-start-hhid", "guest_login_start_hhid", "aws-access-cli_adoption_distinct", {"table": "fact_navigation_interactions", "distinct_expression": "user_id", "extra_where": "AND event_source = 'guestLoginStart'"}),
    MetricSpec("guest-login-cancel-hhid", "guest_login_cancel_hhid", "aws-access-cli_adoption_distinct", {"table": "fact_navigation_interactions", "distinct_expression": "user_id", "extra_where": "AND event_source = 'guestLoginCancel'"}),
)
GAP_HOUSEHOLD_METRICS = HOUSEHOLD_METRICS + (
    MetricSpec("incomplete-no-destroy-hhid", "incomplete_no_destroy_hhid", "aws-access-cli_adoption_playback_outcome", {"distinct_expression": "user_id", "select_identity_columns": "user_id,", "group_identity_columns": "user_id,", "outcome_value": "INCOMPLETE_NO_DESTROY"}),
    MetricSpec("play-stage-error-hhid", "play_stage_error_hhid", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "user_id", "extra_where": "AND event_type = 'PLAY' AND endreason = 'PLAYER_ERROR'"}),
    MetricSpec("play-timeout-hhid", "play_timeout_hhid", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "user_id", "extra_where": "AND event_type = 'PLAY' AND endreason = 'TIMEOUT'"}),
)
GAP_SESSION_METRICS = SESSION_METRICS + (
    MetricSpec("incomplete-no-destroy-sessions", "incomplete_no_destroy_sessions", "aws-access-cli_adoption_playback_outcome", {"distinct_expression": "parent_session_id", "select_identity_columns": "", "group_identity_columns": "", "outcome_value": "INCOMPLETE_NO_DESTROY"}),
    MetricSpec("play-stage-error-sessions", "play_stage_error_sessions", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "parent_session_id", "extra_where": "AND event_type = 'PLAY' AND endreason = 'PLAYER_ERROR'"}),
    MetricSpec("play-timeout-sessions", "play_timeout_sessions", "aws-access-cli_adoption_distinct", {"table": "unified_sessions", "distinct_expression": "parent_session_id", "extra_where": "AND event_type = 'PLAY' AND endreason = 'TIMEOUT'"}),
)


def build_adoption_report(
    athena: AthenaClient,
    catalog: QueryCatalog,
    tenant: TenantConfig,
    start_date: str,
    end_date: str,
    *,
    period: str = "day",
    metrics: tuple[MetricSpec, ...] = HOUSEHOLD_METRICS,
    table_override: str | None = None,
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for metric in metrics:
        sql = _render_metric_sql(catalog, tenant, metric, start_date, end_date, period, table_override=table_override)
        rows = _run_sql(athena, sql)
        _merge_rows(rows, metric.column_header, merged)
    return [merged[session_date] for session_date in sorted(merged)]


def resolve_filename(resolver: PathResolver, artifact: str, *, start_date: str, end_date: str, period: str) -> str:
    if period == "day" and start_date == end_date:
        return resolver.format_snapshot_filename(_iso_date(start_date), artifact)
    return resolver.format_range_filename(_iso_date(start_date), _iso_date(end_date), artifact)


def write_report(
    path: Path,
    writer: CsvWriterProtocol,
    rows: list[dict[str, str]],
    metrics: tuple[MetricSpec, ...] = HOUSEHOLD_METRICS,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["session_date", *[metric.column_header for metric in metrics]]
    writer.write_rows(str(path), rows, fieldnames)
    return path
