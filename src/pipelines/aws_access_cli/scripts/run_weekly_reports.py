"""Thin wrapper for the weekly aws-access-cli orchestrator."""
from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta

from src.lib.logging.bootstrap import init_logging
from src.pipelines.aws_access_cli.schedule import SubReport, catch_up_weeks, run_catch_up
from src.pipelines.aws_access_cli.scripts import (
    run_adoption_report,
    run_adoption_session_report,
    run_guest_session_report,
    run_shaka_error_hhid_report,
    run_shaka_error_session_report,
)
from src.pipelines.aws_access_cli.scripts.common import DEFAULT_RUNTIME, make_auth
from src.pipelines.aws_access_cli.tenants import TenantConfig

_SUB_REPORTS = [
    SubReport('adoption', run_adoption_report.main),
    SubReport('adoption-session', run_adoption_session_report.main),
    SubReport('shaka-hhid', run_shaka_error_hhid_report.main),
    SubReport('shaka-session', run_shaka_error_session_report.main),
    SubReport('guest-session', run_guest_session_report.main),
]


def main(argv: list[str] | None = None) -> int:
    init_logging("aws-access-cli-weekly-reports")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--week', required=True)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--lookback-weeks', type=int, default=4, help='Also fill missing periods this many weeks before the target.')
    parser.add_argument('--no-catch-up', action='store_true', help='Only process the target period.')
    parser.add_argument('--table-suffix', default=None, help="Read each tenant's '<id>_ccl_debug_events_<suffix>' table (e.g. oct26); the week is cut at the last day of its start month.")
    args = parser.parse_args(argv)
    if args.table_suffix and not args.no_catch_up:
        parser.error('--table-suffix requires --no-catch-up (lookback periods would read the wrong month table)')
    def build_argv(value: str, tenant: TenantConfig) -> list[str]:
        force = ['--force'] if args.force and value == values[-1] else []
        if not args.table_suffix:
            return ['--week', value, '--tenant', tenant.code, '--period', 'week', '--skip-auth-check'] + force
        start = date.fromisoformat(value)
        end = min(start + timedelta(days=6), start.replace(day=calendar.monthrange(start.year, start.month)[1]))
        table = f'{tenant.debug_events_table}_{args.table_suffix}'
        return ['--start-date', value, '--end-date', end.isoformat(), '--period', 'week', '--tenant', tenant.code, '--table', table, '--skip-auth-check'] + force

    values = [args.week] if args.no_catch_up else catch_up_weeks(args.week, args.lookback_weeks)
    return run_catch_up(values, build_argv, _SUB_REPORTS, preflight=lambda: make_auth().ensure_session(DEFAULT_RUNTIME.profile))


if __name__ == "__main__":
    raise SystemExit(main())
