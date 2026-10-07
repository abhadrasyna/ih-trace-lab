"""Thin wrapper for the monthly aws-access-cli orchestrator."""
from __future__ import annotations

import argparse

from src.lib.logging.bootstrap import init_logging
from src.pipelines.aws_access_cli.schedule import SubReport, catch_up_months, run_catch_up
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
    init_logging("aws-access-cli-monthly-reports")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', required=True)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--lookback-months', type=int, default=3, help='Also fill missing periods this many months before the target.')
    parser.add_argument('--no-catch-up', action='store_true', help='Only process the target period.')
    args = parser.parse_args(argv)

    def build_argv(value: str, tenant: TenantConfig) -> list[str]:
        return ['--month', value, '--tenant', tenant.code, '--period', 'month', '--skip-auth-check'] + (['--force'] if args.force and value == values[-1] else [])

    values = [args.month] if args.no_catch_up else catch_up_months(args.month, args.lookback_months)
    return run_catch_up(values, build_argv, _SUB_REPORTS, preflight=lambda: make_auth().ensure_session(DEFAULT_RUNTIME.profile))


if __name__ == "__main__":
    raise SystemExit(main())
