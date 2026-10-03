"""Smoke tests for thin wrapper imports."""
from __future__ import annotations

import importlib

WRAPPERS = [
    'src.pipelines.aws_access_cli.scripts.run_adoption_report',
    'src.pipelines.aws_access_cli.scripts.run_adoption_session_report',
    'src.pipelines.aws_access_cli.scripts.run_guest_session_report',
    'src.pipelines.aws_access_cli.scripts.run_shaka_error_hhid_report',
    'src.pipelines.aws_access_cli.scripts.run_shaka_error_session_report',
    'src.pipelines.aws_access_cli.scripts.run_shaka_1xxx_position_report',
    'src.pipelines.aws_access_cli.scripts.run_daily_reports',
    'src.pipelines.aws_access_cli.scripts.run_weekly_reports',
    'src.pipelines.aws_access_cli.scripts.run_monthly_reports',
    'src.pipelines.aws_access_cli.scripts.run_historical_backfill',
    'src.pipelines.aws_access_cli.scripts.run_historical_period_reports',
    'src.pipelines.aws_access_cli.scripts.run_adoption_gap_analysis_report',
    'src.pipelines.aws_access_cli.scripts.run_adoption_gap_analysis_session_report',
    'src.pipelines.aws_access_cli.scripts.run_incomplete_no_destroy_investigation',
    'src.pipelines.aws_access_cli.scripts.run_athena_query',
]


def test_wrappers_import_and_expose_main() -> None:
    for module_name in WRAPPERS:
        module = importlib.import_module(module_name)
        assert callable(module.main)
