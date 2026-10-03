"""Business logic for aws-access-cli Shaka error reports."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from src.lib.athena.protocols import AthenaClient
from src.lib.csv_io.protocols import CsvWriterProtocol
from src.lib.paths.protocols import PathResolver
from src.pipelines.aws_access_cli.catalog import QueryCatalog, quote_sql_literal
from src.pipelines.aws_access_cli.tenants import TenantConfig

_ERROR_CODES = [str(code) for code in range(1001, 1011)]
def _iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _next_date(value: str) -> str:
    return (_iso_date(value) + timedelta(days=1)).isoformat()


def build_shaka_error_report(
    athena: AthenaClient,
    catalog: QueryCatalog,
    tenant: TenantConfig,
    *,
    date_value: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str = "day",
    by: str = "hhid",
    table_override: str | None = None,
) -> list[dict[str, str]]:
    if by not in {"hhid", "session"}:
        raise ValueError("by must be 'hhid' or 'session'")
    if period not in {"day", "week", "month"}:
        raise ValueError("period must be one of 'day', 'week', or 'month'")
    distinct_expression = "split_part(clientid, ':', 2)" if by == "hhid" else "json_extract_scalar(eventdata, '$.sessionid')"
    if date_value is not None:
        start_date = date_value
        end_date = date_value
    if start_date is None or end_date is None:
        raise ValueError("start_date/end_date or date_value is required")
    normalized_start_date = _iso_date(start_date).isoformat()
    normalized_end_date = _iso_date(end_date).isoformat()
    if normalized_end_date < normalized_start_date:
        raise ValueError("end_date must be on or after start_date")
    sql = catalog.render(
        "aws-access-cli_shaka_error_counts",
        {
            "database_identifier": tenant.database,
            "table_identifier": table_override or tenant.debug_events_table,
            "distinct_expression": distinct_expression,
            "time_predicate": (
                f"datetime >= {quote_sql_literal(normalized_start_date + 'T00:00:00.000Z')} AND datetime < {quote_sql_literal(_next_date(normalized_end_date) + 'T00:00:00.000Z')}"
            ),
        },
    )
    execution_id = athena.start_query(sql, {})
    rows = athena.fetch_results(execution_id).rows
    label = "shaka_error_hhid" if by == "hhid" else "shaka_error_session"
    return [
        dict(
            row,
            session_date=normalized_start_date if period != "day" else row.get("session_date", normalized_start_date),
            report_name=row.get("report_name", label),
        )
        for row in rows
    ]


def build_error_1xxx_session_ids(
    athena: AthenaClient,
    catalog: QueryCatalog,
    tenant: TenantConfig,
    date_value: str,
    table_override: str | None = None,
) -> list[dict[str, str]]:
    normalized_date = _iso_date(date_value).isoformat()
    sql = catalog.render(
        "aws-access-cli_error_1xxx_session_ids",
        {
            "database_identifier": tenant.database,
            "table_identifier": table_override or tenant.debug_events_table,
            "error_codes": ", ".join(quote_sql_literal(code) for code in _ERROR_CODES),
            "date": normalized_date,
            "next_date": _next_date(normalized_date),
        },
    )
    execution_id = athena.start_query(sql, {})
    return athena.fetch_results(execution_id).rows


def resolve_filename(resolver: PathResolver, artifact: str, *, start_date: str, end_date: str, period: str) -> str:
    if period == "day" and start_date == end_date:
        return resolver.format_snapshot_filename(_iso_date(start_date), artifact)
    return resolver.format_range_filename(_iso_date(start_date), _iso_date(end_date), artifact)


def write_report(path: Path, writer: CsvWriterProtocol, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["session_date", "errorcode", "metric_value", "report_name"]
    writer.write_rows(str(path), rows, fieldnames)
    return path
