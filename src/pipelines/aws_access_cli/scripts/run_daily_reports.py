"""Thin wrapper for the daily aws-access-cli orchestrator."""
from __future__ import annotations

import argparse

from src.pipelines.aws_access_cli.schedule import SubReport, run_for_all_tenants
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True)
    args = parser.parse_args(argv)

    def build_argv(tenant: TenantConfig) -> list[str]:
        return ['--date', args.date, '--tenant', tenant.code, '--skip-auth-check']

    return run_for_all_tenants(build_argv, _SUB_REPORTS, preflight=lambda: make_auth().ensure_session(DEFAULT_RUNTIME.profile))


if __name__ == "__main__":
    raise SystemExit(main())
