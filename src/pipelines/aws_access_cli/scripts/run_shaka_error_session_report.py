"""Thin wrapper for run_shaka_error_session_report."""
from __future__ import annotations

from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import current_fcid
from src.pipelines.aws_access_cli.scripts.common import run_shaka_cli


def main(argv: list[str] | None = None) -> int:
    if current_fcid() is None:
        init_logging("aws-access-cli-shaka-error-session-report")
    return run_shaka_cli(argv, artifact='shaka-error-session', by='session')


if __name__ == "__main__":
    raise SystemExit(main())
