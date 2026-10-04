"""Thin wrapper for run_shaka_1xxx_position_report."""
from __future__ import annotations

from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import current_fcid
from src.pipelines.aws_access_cli.scripts.common import run_position_cli


def main(argv: list[str] | None = None) -> int:
    if current_fcid() is None:
        init_logging("aws-access-cli-shaka-1xxx-position-report")
    return run_position_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
