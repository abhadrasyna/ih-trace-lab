"""Thin orchestration helpers for daily/weekly/monthly/backfill wrappers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

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
