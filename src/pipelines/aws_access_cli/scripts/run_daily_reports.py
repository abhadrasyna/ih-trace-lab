"""Thin wrapper for the daily aws-access-cli orchestrator."""
from __future__ import annotations

import argparse

from src.lib.logging.bootstrap import init_logging
from src.pipelines.aws_access_cli.schedule import SubReport, catch_up_days, run_catch_up
from src.pipelines.aws_access_cli.scripts import (
    run_adoption_report,
    run_adoption_session_report,
    run_guest_session_report,
    run_shaka_1xxx_position_report,
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
    SubReport('shaka-1xxx-position', run_shaka_1xxx_position_report.main),
]


def main(argv: list[str] | None = None) -> int:
    init_logging("aws-access-cli-daily-reports")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--lookback-days', type=int, default=7, help='Also fill missing periods this many days before the target.')
    parser.add_argument('--no-catch-up', action='store_true', help='Only process the target period.')
    parser.add_argument('--retry-blank-days', type=int, default=3, help='Re-run adoption dates with blank cells if at most this many days old (all sub-reports accept the flag via base_parser; only adoption ones use it).')
    args = parser.parse_args(argv)

    def build_argv(value: str, tenant: TenantConfig) -> list[str]:
        base = ['--date', value, '--tenant', tenant.code, '--skip-auth-check', '--retry-blank-days', str(args.retry_blank_days)]
        return base + (['--force'] if args.force and value == values[-1] else [])

    values = [args.date] if args.no_catch_up else catch_up_days(args.date, args.lookback_days)
    return run_catch_up(values, build_argv, _SUB_REPORTS, preflight=lambda: make_auth().ensure_session(DEFAULT_RUNTIME.profile))


if __name__ == "__main__":
    raise SystemExit(main())
