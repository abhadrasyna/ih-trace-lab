"""Shared CLI helpers for the thin aws-access-cli wrappers."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.lib.csv_io.monthly_store import MonthlyCsvStore
from src.lib.report_render.factory import make_report_writer
from src.pipelines.aws_access_cli.adoption import (
    GAP_HOUSEHOLD_METRICS,
    GAP_SESSION_METRICS,
    GUEST_METRICS,
    HOUSEHOLD_METRICS,
    SESSION_METRICS,
    MetricSpec,
    build_adoption_report,
)
from src.pipelines.aws_access_cli.adoption import (
    resolve_filename as resolve_adoption_filename,
)
from src.pipelines.aws_access_cli.adoption import (
    write_report as write_adoption_report,
)
from src.pipelines.aws_access_cli.catalog import QueryCatalog, comma_join_quoted
from src.pipelines.aws_access_cli.position_report import run_position_report
from src.pipelines.aws_access_cli.runtime import (
    RuntimeConfig,
    make_athena_client,
    make_auth,
    make_csv_reader,
    make_csv_writer,
    make_path_resolver,
    repo_root,
)
from src.pipelines.aws_access_cli.shaka_errors import (
    build_shaka_error_report,
)
from src.pipelines.aws_access_cli.shaka_errors import (
    resolve_filename as resolve_shaka_filename,
)
from src.pipelines.aws_access_cli.shaka_errors import (
    write_report as write_shaka_report,
)
from src.pipelines.aws_access_cli.tenants import TENANTS_BY_CODE, get_tenant

DEFAULT_RUNTIME = RuntimeConfig()
_SESSION_ID_BATCH_SIZE = 250
# Artifacts whose `--period day` runs append into a single `<yyyy-mm>_<artifact>.csv` month
# file (one row-set per date, upserted) instead of each day getting its own snapshot file --
# matching the pre-migration `aws-access-cli`'s month-file behavior for these 5 reports (see
# `docs/archive/src-lib-migration/`). Gap-analysis variants and the position report keep the
# per-day snapshot file, unchanged.
_MONTHLY_APPEND_ARTIFACTS = frozenset(
    {
        "adoption-report",
        "adoption-session-report",
        "guest-session-report",
        "shaka-error-hhid",
        "shaka-error-session",
    }
)


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--date", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--week", default=None)
    parser.add_argument("--month", default=None)
    parser.add_argument("--period", default="day", choices=("day", "week", "month"))
    parser.add_argument("--tenant", default=None, choices=sorted(TENANTS_BY_CODE))
    parser.add_argument("--table", default=None)
    parser.add_argument("--profile", default=DEFAULT_RUNTIME.profile)
    parser.add_argument("--workgroup", default=DEFAULT_RUNTIME.workgroup)
    parser.add_argument("--output-location", default=DEFAULT_RUNTIME.output_location)
    parser.add_argument("--output-dir", default=DEFAULT_RUNTIME.output_dir)
    parser.add_argument("--log-dir", default=DEFAULT_RUNTIME.log_dir)
    parser.add_argument("--region", default=DEFAULT_RUNTIME.region)
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_RUNTIME.poll_interval)
    parser.add_argument("--timeout", type=int, default=DEFAULT_RUNTIME.timeout)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--skip-auth-check", action="store_true")
    return parser


def resolve_range(args: argparse.Namespace) -> tuple[str, str, str]:
    def _validated_pair(start: str, end: str, period: str) -> tuple[str, str, str]:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        return start_date.isoformat(), end_date.isoformat(), period

    if args.date:
        if args.period == "week":
            start_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            return _validated_pair(start_date.isoformat(), (start_date + timedelta(days=6)).isoformat(), "week")
        if args.period == "month":
            month_start = datetime.strptime(args.date, "%Y-%m-%d").date().replace(day=1)
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return _validated_pair(month_start.isoformat(), (next_month - timedelta(days=1)).isoformat(), "month")
        return _validated_pair(args.date, args.date, "day")
    if args.start_date and args.end_date:
        return _validated_pair(args.start_date, args.end_date, args.period)
    if args.week:
        start_date = datetime.strptime(args.week, "%Y-%m-%d").date()
        return _validated_pair(start_date.isoformat(), (start_date + timedelta(days=6)).isoformat(), "week")
    if args.month:
        month_start = datetime.strptime(f"{args.month}-01", "%Y-%m-%d").date()
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return _validated_pair(month_start.isoformat(), (next_month - timedelta(days=1)).isoformat(), "month")
    raise ValueError("One of --date, --start-date/--end-date, --week, or --month is required")


def render_summary(rows: list[dict[str, str]]) -> str:
    preview = rows[:5]
    return make_report_writer("markdown_table").render(preview or [{"status": "no rows"}])


def _maybe_print_preview(rows: list[dict[str, str]], *, enabled: bool) -> None:
    if enabled:
        print(render_summary(rows))


def _runtime_from_args(args: argparse.Namespace) -> RuntimeConfig:
    return RuntimeConfig(
        profile=args.profile,
        workgroup=args.workgroup,
        output_location=args.output_location,
        region=args.region,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
    )


def _base_output_dir(args: argparse.Namespace, period: str) -> Path:
    base_dir = Path(args.output_dir)
    if not base_dir.is_absolute():
        base_dir = repo_root() / base_dir
    return base_dir / get_tenant(args.tenant).code / ({"day": "daily", "week": "weekly", "month": "monthly"}[period])


def _end_date_exclusive(value: str) -> str:
    return (datetime.strptime(value, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()


def _print_dry_run(label: str, output_path: Path, details: dict[str, Any]) -> int:
    detail_lines = "\n".join(f"{key}: {value}" for key, value in details.items())
    print(f"DRY RUN {label}\noutput: {output_path}\n{detail_lines}")
    return 0


def _batched(values: list[str], batch_size: int = _SESSION_ID_BATCH_SIZE) -> list[list[str]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def _is_monthly_append(artifact: str, *, period: str, start_date: str, end_date: str) -> bool:
    """Whether `artifact`'s `--period day` run should append into its month file.

    Only a single-date `day` run can be merged into one date-keyed row-set; week/month runs
    already aggregate the whole range into one fixed-name file, unchanged.
    """
    return period == "day" and start_date == end_date and artifact in _MONTHLY_APPEND_ARTIFACTS


def _resolve_output_path(
    resolver: Any,
    args: argparse.Namespace,
    artifact: str,
    *,
    start_date: str,
    end_date: str,
    period: str,
    snapshot_filename: str,
) -> Path:
    if _is_monthly_append(artifact, period=period, start_date=start_date, end_date=end_date):
        filename = resolver.format_month_filename(datetime.strptime(start_date, "%Y-%m-%d").date(), artifact)
    else:
        filename = snapshot_filename
    return _base_output_dir(args, period) / filename


def run_adoption_cli(argv: list[str] | None, *, artifact: str, metrics: tuple[MetricSpec, ...]) -> int:
    args = base_parser(f"Run {artifact}").parse_args(argv)
    start_date, end_date, period = resolve_range(args)
    tenant = get_tenant(args.tenant)
    resolver = make_path_resolver()
    filename = resolve_adoption_filename(resolver, artifact, start_date=start_date, end_date=end_date, period=period)
    output_path = _resolve_output_path(resolver, args, artifact, start_date=start_date, end_date=end_date, period=period, snapshot_filename=filename)
    if args.dry_run:
        return _print_dry_run(
            artifact,
            output_path,
            {"tenant": tenant.code, "start_date": start_date, "end_date": end_date, "period": period},
        )
    if not args.skip_auth_check:
        make_auth().ensure_session(args.profile)
    catalog = QueryCatalog()
    athena = make_athena_client(_runtime_from_args(args), tenant.database)
    rows = build_adoption_report(athena, catalog, tenant, start_date, end_date, period=period, metrics=metrics, table_override=args.table)
    if _is_monthly_append(artifact, period=period, start_date=start_date, end_date=end_date):
        fieldnames = ["session_date", *[metric.column_header for metric in metrics]]
        MonthlyCsvStore(make_csv_reader(), make_csv_writer()).replace_date(output_path, start_date, rows, field_order=fieldnames)
    else:
        write_adoption_report(output_path, make_csv_writer(), rows, metrics)
    _maybe_print_preview(rows, enabled=args.preview)
    return 0


def run_shaka_cli(argv: list[str] | None, *, artifact: str, by: str) -> int:
    args = base_parser(f"Run {artifact}").parse_args(argv)
    start_date, end_date, period = resolve_range(args)
    tenant = get_tenant(args.tenant)
    resolver = make_path_resolver()
    filename = resolve_shaka_filename(resolver, artifact, start_date=start_date, end_date=end_date, period=period)
    output_path = _resolve_output_path(resolver, args, artifact, start_date=start_date, end_date=end_date, period=period, snapshot_filename=filename)
    if args.dry_run:
        return _print_dry_run(
            artifact,
            output_path,
            {"tenant": tenant.code, "start_date": start_date, "end_date": end_date, "period": period, "group_by": by},
        )
    if not args.skip_auth_check:
        make_auth().ensure_session(args.profile)
    rows = build_shaka_error_report(
        make_athena_client(_runtime_from_args(args), tenant.database),
        QueryCatalog(),
        tenant,
        date_value=start_date if start_date == end_date and period == "day" else None,
        start_date=start_date,
        end_date=end_date,
        period=period,
        by=by,
        table_override=args.table,
    )
    if _is_monthly_append(artifact, period=period, start_date=start_date, end_date=end_date):
        MonthlyCsvStore(make_csv_reader(), make_csv_writer()).replace_date(
            output_path, start_date, rows, field_order=["session_date", "errorcode", "metric_value", "report_name"]
        )
    else:
        write_shaka_report(output_path, make_csv_writer(), rows)
    _maybe_print_preview(rows, enabled=args.preview)
    return 0


def run_position_cli(argv: list[str] | None) -> int:
    args = base_parser("Run shaka 1xxx position report").parse_args(argv)
    start_date, end_date, period = resolve_range(args)
    if period != "day" or start_date != end_date:
        raise ValueError("Position report only supports a single --date run")
    tenant = get_tenant(args.tenant)
    resolver = make_path_resolver()
    filename = resolver.format_snapshot_filename(datetime.strptime(start_date, "%Y-%m-%d").date(), "shaka-1xxx-position-report")
    output_path = _base_output_dir(args, period) / filename
    if args.dry_run:
        return _print_dry_run("shaka-1xxx-position-report", output_path, {"tenant": tenant.code, "date": start_date})
    if not args.skip_auth_check:
        make_auth().ensure_session(args.profile)
    rows = run_position_report(make_athena_client(_runtime_from_args(args), tenant.database), QueryCatalog(), tenant, start_date, table_override=args.table)
    write_shaka_report(output_path, make_csv_writer(), rows)
    _maybe_print_preview(rows, enabled=args.preview)
    return 0


def run_incomplete_investigation_cli(argv: list[str] | None) -> int:
    args = base_parser("Run incomplete no destroy investigation").parse_args(argv)
    start_date, end_date, period = resolve_range(args)
    tenant = get_tenant(args.tenant)
    output_dir = _base_output_dir(args, period)
    resolver = make_path_resolver()
    session_filename = (
        resolver.format_snapshot_filename(datetime.strptime(start_date, "%Y-%m-%d").date(), "incomplete-no-destroy-session-ids")
        if start_date == end_date
        else resolver.format_range_filename(
            datetime.strptime(start_date, "%Y-%m-%d").date(),
            datetime.strptime(end_date, "%Y-%m-%d").date(),
            "incomplete-no-destroy-session-ids",
        )
    )
    debug_filename = (
        resolver.format_snapshot_filename(datetime.strptime(start_date, "%Y-%m-%d").date(), "session-debug-events")
        if start_date == end_date
        else resolver.format_range_filename(
            datetime.strptime(start_date, "%Y-%m-%d").date(),
            datetime.strptime(end_date, "%Y-%m-%d").date(),
            "session-debug-events",
        )
    )
    if args.dry_run:
        return _print_dry_run(
            "incomplete-no-destroy-investigation",
            output_dir / session_filename,
            {"tenant": tenant.code, "start_date": start_date, "end_date": end_date, "period": period},
        )
    if not args.skip_auth_check:
        make_auth().ensure_session(args.profile)
    athena = make_athena_client(_runtime_from_args(args), tenant.database)
    catalog = QueryCatalog()
    sql = catalog.render(
        'aws-access-cli_incomplete_no_destroy_session_ids',
        {
            'database_identifier': tenant.database,
            'start_date': start_date,
            'end_date_exclusive': _end_date_exclusive(end_date),
        },
    )
    session_rows = athena.fetch_results(athena.start_query(sql, {})).rows
    session_ids = sorted({row['session_id'] for row in session_rows if row.get('session_id')})
    debug_rows: list[dict[str, str]] = []
    for session_batch in _batched(session_ids):
        debug_sql = catalog.render(
            'aws-access-cli_session_debug_events',
            {
                'database_identifier': tenant.database,
                'table_identifier': args.table or tenant.debug_events_table,
                'id_list': comma_join_quoted(session_batch),
                'start_date': start_date,
                'end_date_exclusive': _end_date_exclusive(end_date),
            },
        )
        debug_rows.extend(athena.fetch_results(athena.start_query(debug_sql, {})).rows)
    writer = make_csv_writer()
    output_dir.mkdir(parents=True, exist_ok=True)
    writer.write_rows(str(output_dir / session_filename), session_rows, list(session_rows[0]) if session_rows else ['session_date', 'session_id'])
    writer.write_rows(str(output_dir / debug_filename), debug_rows, list(debug_rows[0]) if debug_rows else ['datetime', 'eventclass', 'eventid', 'clientid', 'session_id', 'eventdata'])
    _maybe_print_preview(session_rows, enabled=args.preview)
    return 0


def run_query_cli(argv: list[str] | None) -> int:
    parser = base_parser("Run one catalog query")
    parser.add_argument('query_name')
    parser.add_argument('--param', action='append', default=[])
    args = parser.parse_args(argv)
    for item in args.param:
        if "=" not in item:
            raise ValueError(f"--param entries must be KEY=VALUE, got {item!r}")
    raw_params = dict(item.split('=', 1) for item in args.param)
    tenant = get_tenant(args.tenant)
    resolved_range: tuple[str, str, str] | None = None
    render_params = dict(raw_params)
    if args.date or args.start_date or args.end_date or args.week or args.month:
        start_date, end_date, period = resolve_range(args)
        resolved_range = (start_date, end_date, period)
        render_params.update(
            {
                "date": start_date,
                "start_date": start_date,
                "end_date": end_date,
                "end_date_exclusive": _end_date_exclusive(end_date),
            }
        )
    catalog = QueryCatalog()
    sql = catalog.render(
        args.query_name,
        {**render_params, 'database_identifier': tenant.database, 'table_identifier': args.table or tenant.debug_events_table},
    )
    if args.dry_run:
        print(sql)
        return 0
    if not args.skip_auth_check:
        make_auth().ensure_session(args.profile)
    athena = make_athena_client(_runtime_from_args(args), tenant.database)
    resolver = make_path_resolver()
    if resolved_range is not None:
        start_date, end_date, period = resolved_range
        output_dir = _base_output_dir(args, period)
        if start_date == end_date:
            filename = resolver.format_snapshot_filename(datetime.strptime(start_date, "%Y-%m-%d").date(), args.query_name)
        else:
            filename = resolver.format_range_filename(
                datetime.strptime(start_date, "%Y-%m-%d").date(),
                datetime.strptime(end_date, "%Y-%m-%d").date(),
                args.query_name,
            )
    else:
        output_dir = _base_output_dir(args, args.period)
        filename = resolver.format_rollup_filename(args.query_name)
    output_path = output_dir / filename
    rows = athena.fetch_results(athena.start_query(sql, {})).rows
    write_shaka_report(output_path, make_csv_writer(), rows)
    _maybe_print_preview(rows, enabled=args.preview)
    return 0


def adoption_metrics(kind: str) -> tuple[MetricSpec, ...]:
    return {
        'household': HOUSEHOLD_METRICS,
        'session': SESSION_METRICS,
        'guest': GUEST_METRICS,
        'gap-household': GAP_HOUSEHOLD_METRICS,
        'gap-session': GAP_SESSION_METRICS,
    }[kind]


def tenant_argv(date_flag: str, date_value: str, tenant_code: str, *, period: str | None = None) -> list[str]:
    argv = [date_flag, date_value, '--tenant', tenant_code, '--skip-auth-check']
    if period is not None:
        argv.extend(['--period', period])
    return argv
