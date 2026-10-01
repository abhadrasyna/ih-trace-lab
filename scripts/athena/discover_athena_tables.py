#!/usr/bin/env python3
"""CLI to discover every table in an Athena database via ``SHOW TABLES``.

Ported from the read-only ``github_copilot/oasis-athena-mcp`` workspace so this repository can keep the same
table-discovery workflow alongside the future query-catalog DDL cache. Like the source version, it stays
project-agnostic: every AWS-facing flag must be supplied explicitly, and this task does not execute the script against a
live service.

Writes a one-column ``table_name`` CSV. That CSV is the input for a knowledge doc's table-inventory/categorization
section, and for ``run_table_ddl_export.py --tables-csv``.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"
_DEFAULT_POLL_INTERVAL_SECONDS = 2
_DEFAULT_TIMEOUT_SECONDS = 300

_LOGGER = logging.getLogger("scripts.athena.discover_athena_tables")


class AthenaDependencyError(RuntimeError):
    """Raised when the shared Athena execution stack is not yet wired into this repo."""


@dataclass(frozen=True)
class AthenaDependencies:
    """Runtime-only Athena modules loaded lazily so this script remains importable before integration lands."""

    athena_cli_common: Any
    config_lib: Any


def _load_athena_dependencies() -> AthenaDependencies:
    """Import Athena runtime dependencies only when the CLI is actually executed."""

    try:
        import athena_cli_common  # type: ignore[import-not-found]
        from athena_runner import config as config_lib  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise AthenaDependencyError(
            "This ported CLI depends on athena_cli_common and athena_runner from the future Athena integration. "
            "QC-4 ports the entrypoint without running live Athena queries."
        ) from exc

    return AthenaDependencies(athena_cli_common=athena_cli_common, config_lib=config_lib)


def _load_setup_logging() -> Any:
    """Import the repo's shared logging setup only after the repo root is on ``sys.path``."""

    from logs.setup_logging import setup_logging

    return setup_logging


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the table-discovery CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Athena database/catalog to discover tables in.")
    parser.add_argument("--profile", required=True, help="AWS SSO profile to run the query as.")
    parser.add_argument("--workgroup", required=True, help="Athena workgroup to run under.")
    parser.add_argument("--output-location", required=True, help="S3 URI for Athena's raw query results.")
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region override; defaults to the profile's own region.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help=f"Local directory for the CSV when --output is omitted (default: {_DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="CSV path to write (table_name); defaults to <output-dir>/<database>_tables.csv.",
    )
    parser.add_argument(
        "--skip-auth-check",
        action="store_true",
        help="Skip the pre-flight SSO credential check/auto-refresh.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Standard logging level name for this repo's shared logger (default: INFO).",
    )
    return parser.parse_args(argv)


def discover_tables(executor: Any, downloader: Any, database: str) -> list[str]:
    """Return every table name in ``database`` via ``SHOW TABLES``."""

    athena_cli_common = _load_athena_dependencies().athena_cli_common
    lines = athena_cli_common.run_and_read_lines(executor, downloader, f"SHOW TABLES IN {database}", database)
    return [line.strip() for line in lines if line.strip()]


def write_tables_csv(tables: list[str], output_path: str) -> None:
    """Write ``tables`` as a one-column ``table_name`` CSV to ``output_path``."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["table_name"])
        for table in tables:
            writer.writerow([table])


def main(argv: Sequence[str] | None = None) -> int:
    """Discover every table in ``--database`` and write it to a CSV."""

    args = _parse_args(argv)
    _load_setup_logging()(level=args.log_level)

    try:
        dependencies = _load_athena_dependencies()
    except AthenaDependencyError as exc:
        print(exc, file=sys.stderr)
        return 1

    run_config = dependencies.config_lib.RunConfig(
        profile=args.profile,
        workgroup=args.workgroup,
        output_location=args.output_location,
        output_dir=args.output_dir,
        region=args.region,
        poll_interval_seconds=_DEFAULT_POLL_INTERVAL_SECONDS,
        timeout_seconds=_DEFAULT_TIMEOUT_SECONDS,
    )

    if not args.skip_auth_check and not dependencies.athena_cli_common.ensure_sso_or_log_failure(run_config, _LOGGER):
        return 1

    executor, downloader = dependencies.athena_cli_common.build_executor(run_config)
    tables = discover_tables(executor, downloader, args.database)
    _LOGGER.info("Discovered %d table(s) in %s", len(tables), args.database)

    output_path = args.output or str(Path(args.output_dir) / f"{args.database}_tables.csv")
    write_tables_csv(tables, output_path)
    _LOGGER.info("Wrote %d table name(s) to %s", len(tables), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
