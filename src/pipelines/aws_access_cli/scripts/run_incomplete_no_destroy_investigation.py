"""Thin wrapper for run_incomplete_no_destroy_investigation."""
from __future__ import annotations

from src.pipelines.aws_access_cli.scripts.common import run_incomplete_investigation_cli


def main(argv: list[str] | None = None) -> int:
    return run_incomplete_investigation_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
