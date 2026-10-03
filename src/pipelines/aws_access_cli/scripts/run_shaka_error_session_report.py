"""Thin wrapper for run_shaka_error_session_report."""
from __future__ import annotations

from src.pipelines.aws_access_cli.scripts.common import run_shaka_cli


def main(argv: list[str] | None = None) -> int:
    return run_shaka_cli(argv, artifact='shaka-error-session', by='session')


if __name__ == "__main__":
    raise SystemExit(main())
