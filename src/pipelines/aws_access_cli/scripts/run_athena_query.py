"""Thin wrapper for run_athena_query."""
from __future__ import annotations

from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import current_fcid
from src.pipelines.aws_access_cli.scripts.common import run_query_cli


def main(argv: list[str] | None = None) -> int:
    if current_fcid() is None:
        init_logging("aws-access-cli-athena-query")
    return run_query_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
