"""Thin wrapper for run_adoption_report."""
from __future__ import annotations

from src.pipelines.aws_access_cli.adoption import HOUSEHOLD_METRICS
from src.pipelines.aws_access_cli.scripts.common import run_adoption_cli


def main(argv: list[str] | None = None) -> int:
    return run_adoption_cli(argv, artifact='adoption-report', metrics=HOUSEHOLD_METRICS)


if __name__ == "__main__":
    raise SystemExit(main())
