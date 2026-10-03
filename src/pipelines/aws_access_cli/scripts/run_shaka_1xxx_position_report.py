"""Thin wrapper for run_shaka_1xxx_position_report."""
from __future__ import annotations

from src.pipelines.aws_access_cli.scripts.common import run_position_cli


def main(argv: list[str] | None = None) -> int:
    return run_position_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
