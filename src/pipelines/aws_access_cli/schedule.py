"""Thin orchestration helpers for daily/weekly/monthly/backfill wrappers."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.pipelines.aws_access_cli.tenants import TenantConfig, all_tenants

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubReport:
    name: str
    runner: Callable[[list[str]], int]


def run_for_all_tenants(
    build_argv: Callable[[TenantConfig], list[str]],
    sub_reports: list[SubReport],
    *,
    preflight: Callable[[], None] | None = None,
) -> int:
    exit_code = 0
    if preflight is not None:
        preflight()
    for tenant in all_tenants():
        for report in sub_reports:
            try:
                result = report.runner(build_argv(tenant))
            except SystemExit as exc:
                raw_code = exc.code
                result = 0 if raw_code is None else int(raw_code) if isinstance(raw_code, int) and raw_code == 0 else 1
                if result != 0:
                    LOGGER.error(
                        "Scheduled sub-report exited non-zero",
                        extra={"tenant": tenant.code, "report": report.name, "exit_code": raw_code},
                    )
            except Exception:
                LOGGER.exception("Scheduled sub-report failed", extra={"tenant": tenant.code, "report": report.name})
                result = 1
            exit_code = max(exit_code, result)
    return exit_code


def catch_up_days(anchor: str, lookback: int) -> list[str]:
    """Dates from `anchor - lookback` through `anchor`, oldest first."""
    end = datetime.strptime(anchor, "%Y-%m-%d").date()
    return [(end - timedelta(days=n)).isoformat() for n in range(max(lookback, 0), -1, -1)]


def catch_up_weeks(anchor: str, lookback: int) -> list[str]:
    """Week-start dates from `anchor - lookback weeks` through `anchor`, oldest first."""
    end = datetime.strptime(anchor, "%Y-%m-%d").date()
    return [(end - timedelta(weeks=n)).isoformat() for n in range(max(lookback, 0), -1, -1)]


def catch_up_months(anchor: str, lookback: int) -> list[str]:
    """`YYYY-MM` values from `anchor - lookback months` through `anchor`, oldest first."""
    end = datetime.strptime(f"{anchor}-01", "%Y-%m-%d").date()
    index = end.year * 12 + end.month - 1
    return [f"{(index - n) // 12:04d}-{(index - n) % 12 + 1:02d}" for n in range(max(lookback, 0), -1, -1)]


def run_catch_up(
    values: list[str],
    build_argv: Callable[[str, TenantConfig], list[str]],
    sub_reports: list[SubReport],
    *,
    preflight: Callable[[], None] | None = None,
) -> int:
    """Run every period in `values`; sub-reports skip periods whose output already has data."""
    exit_code = 0
    for position, value in enumerate(values):
        LOGGER.info("Processing period", extra={"period_value": value})
        exit_code = max(
            exit_code,
            run_for_all_tenants(
                lambda tenant, value=value: build_argv(value, tenant),
                sub_reports,
                preflight=preflight if position == 0 else None,
            ),
        )
    return exit_code
