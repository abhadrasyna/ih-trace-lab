"""Thin wrapper for run_incomplete_no_destroy_investigation."""
from __future__ import annotations

from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import current_fcid
from src.pipelines.aws_access_cli.scripts.common import run_incomplete_investigation_cli


def main(argv: list[str] | None = None) -> int:
    if current_fcid() is None:
        init_logging("aws-access-cli-incomplete-no-destroy-investigation")
    return run_incomplete_investigation_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
