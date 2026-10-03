"""Thin wrapper for run_athena_query."""
from __future__ import annotations

from src.pipelines.aws_access_cli.scripts.common import run_query_cli


def main(argv: list[str] | None = None) -> int:
    return run_query_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
