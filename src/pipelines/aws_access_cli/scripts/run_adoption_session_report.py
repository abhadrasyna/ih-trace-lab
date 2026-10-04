"""Thin wrapper for run_adoption_session_report."""
from __future__ import annotations

from src.pipelines.aws_access_cli.adoption import SESSION_METRICS
from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import current_fcid
from src.pipelines.aws_access_cli.scripts.common import run_adoption_cli


def main(argv: list[str] | None = None) -> int:
    if current_fcid() is None:
        init_logging("aws-access-cli-adoption-session-report")
    return run_adoption_cli(argv, artifact='adoption-session-report', metrics=SESSION_METRICS)


if __name__ == "__main__":
    raise SystemExit(main())
