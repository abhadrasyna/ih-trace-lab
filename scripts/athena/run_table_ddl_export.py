#!/usr/bin/env python3
"""CLI to export ``SHOW CREATE TABLE`` DDL for every table in an Athena database as one CSV.

Ported from the read-only ``github_copilot/oasis-athena-mcp`` workspace so this repository can reuse the same
discover/filter/export workflow when a real Athena tenant is available. Like the source version, it is project-agnostic
and requires every AWS-facing flag explicitly; QC-4 ports the file only and does not run it against a live service.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import logging
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"
_DEFAULT_BATCH_SIZE = 10

_LOGGER = logging.getLogger("scripts.athena.run_table_ddl_export")


class AthenaDependencyError(RuntimeError):
    """Raised when the shared Athena execution stack is not yet wired into this repo."""


@dataclasses.dataclass(frozen=True)
class AthenaDependencies:
    """Runtime-only Athena modules loaded lazily so this script remains importable before integration lands."""

    athena_cli_common: Any
    config_lib: Any
    exceptions: Any


def _load_athena_dependencies() -> AthenaDependencies:
    """Import Athena runtime dependencies only when the CLI is actually executed."""

    try:
        import athena_cli_common  # type: ignore[import-not-found]
        from athena_runner import config as config_lib  # type: ignore[import-not-found]
        from athena_runner import exceptions  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise AthenaDependencyError(
            "This ported CLI depends on athena_cli_common and athena_runner from the future Athena integration. "
            "QC-4 ports the entrypoint without running live Athena queries."
        ) from exc

    return AthenaDependencies(
        athena_cli_common=athena_cli_common,
        config_lib=config_lib,
        exceptions=exceptions,
    )


def _load_setup_logging() -> Any:
    """Import the repo's shared logging setup only after the repo root is on ``sys.path``."""

    from logs.setup_logging import setup_logging

    return setup_logging


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the table-DDL exporter."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Athena database/catalog to export DDL from.")
    tables_group = parser.add_mutually_exclusive_group()
    tables_group.add_argument(
        "--tables",
        default=None,
        help="Comma-separated table names to export; omitted means discover every table via SHOW TABLES.",
    )
    tables_group.add_argument(
        "--tables-csv",
        default=None,
        help="Path to a one-column table_name CSV as written by discover_athena_tables.py.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=_DEFAULT_BATCH_SIZE,
        help=f"Number of tables per batch, with auth refresh + flush between batches (default: {_DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="CSV path to write (table_name, ddl); defaults to <output-dir>/<database>_table_ddl.csv.",
    )
    parser.add_argument("--profile", required=True, help="AWS SSO profile to run queries as.")
    parser.add_argument("--workgroup", required=True, help="Athena workgroup to run under.")
    parser.add_argument("--output-location", required=True, help="S3 URI for Athena's raw query results.")
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help=f"Local directory for the CSV when --output is omitted (default: {_DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region override; defaults to the profile's own region.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=2,
        help="Seconds between status polls (default: 2).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Max seconds to wait for each query's completion (default: 300).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the tables that would be exported and exit, without touching Athena.",
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


def _read_tables_csv(csv_path: str) -> list[str]:
    """Read a one-column ``table_name`` CSV, as written by ``discover_athena_tables.py``."""

    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "table_name" not in reader.fieldnames:
            raise ValueError(f"{csv_path} must have a 'table_name' column, got {reader.fieldnames}")
        return [row["table_name"] for row in reader if row["table_name"].strip()]


def discover_tables(executor: Any, downloader: Any, database: str) -> list[str]:
    """Return every table name in ``database`` via ``SHOW TABLES``."""

    athena_cli_common = _load_athena_dependencies().athena_cli_common
    lines = athena_cli_common.run_and_read_lines(executor, downloader, f"SHOW TABLES IN {database}", database)
    return [line.strip() for line in lines if line.strip()]


def fetch_table_ddl(executor: Any, downloader: Any, database: str, table: str) -> str:
    """Return the full ``SHOW CREATE TABLE`` DDL text for ``database.table``."""

    athena_cli_common = _load_athena_dependencies().athena_cli_common
    lines = athena_cli_common.run_and_read_lines(executor, downloader, f"SHOW CREATE TABLE {database}.{table}", database)
    return "\n".join(lines)


def _chunked(items: Sequence[str], batch_size: int) -> Iterator[list[str]]:
    """Yield ``items`` split into consecutive lists of at most ``batch_size``."""

    for start in range(0, len(items), batch_size):
        yield list(items[start : start + batch_size])


@dataclasses.dataclass(frozen=True)
class ExportContext:
    """Bundle the shared dependencies for one ``export_table_ddl`` call."""

    executor: Any
    downloader: Any
    run_config: Any
    database: str


def export_table_ddl(context: ExportContext, tables: list[str], output_path: str, batch_size: int, skip_auth_check: bool) -> None:
    """Fetch DDL for every entry in ``tables`` and write it to ``output_path``."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["table_name", "ddl"])
        handle.flush()
        processed = 0
        for batch_index, batch in enumerate(_chunked(tables, batch_size)):
            if batch_index > 0 and not skip_auth_check:
                _reauth_or_raise(context.run_config, processed, len(tables), output_path)
            processed = _export_batch(context, batch, writer, processed, len(tables))
            handle.flush()


def _reauth_or_raise(run_config: Any, processed: int, total: int, output_path: str) -> None:
    """Re-check or refresh SSO before a batch; raise if that fails."""

    dependencies = _load_athena_dependencies()
    if not dependencies.athena_cli_common.ensure_sso_or_log_failure(run_config, _LOGGER):
        raise dependencies.exceptions.SsoLoginError(
            "SSO credential refresh failed between batches -- "
            f"{processed}/{total} table(s) already saved to {output_path}"
        )


def _export_batch(context: ExportContext, batch: list[str], writer: csv.writer, processed: int, total: int) -> int:
    """Fetch DDL for one batch of tables, writing each row as it goes."""

    dependencies = _load_athena_dependencies()
    query_errors = (
        dependencies.exceptions.QueryExecutionError,
        dependencies.exceptions.QueryTimeoutError,
    )

    for table in batch:
        processed += 1
        _LOGGER.info("[%d/%d] Fetching DDL for %s.%s", processed, total, context.database, table)
        try:
            ddl = fetch_table_ddl(context.executor, context.downloader, context.database, table)
        except query_errors as exc:
            _LOGGER.error("Failed to fetch DDL for %s: %s", table, exc)
            ddl = f"ERROR: {exc}"
        writer.writerow([table, ddl])
    return processed


def main(argv: Sequence[str] | None = None) -> int:
    """Export every requested table's DDL as a CSV."""

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
        poll_interval_seconds=args.poll_interval,
        timeout_seconds=args.timeout,
    )

    if args.tables_csv:
        requested_tables = _read_tables_csv(args.tables_csv)
    elif args.tables:
        requested_tables = [name.strip() for name in args.tables.split(",") if name.strip()]
    else:
        requested_tables = None

    if args.dry_run and requested_tables is not None:
        for table in requested_tables:
            print(table)
        return 0

    if not args.skip_auth_check and not dependencies.athena_cli_common.ensure_sso_or_log_failure(run_config, _LOGGER):
        return 1

    executor, downloader = dependencies.athena_cli_common.build_executor(run_config)

    tables = requested_tables
    if tables is None:
        tables = discover_tables(executor, downloader, args.database)
        _LOGGER.info("Discovered %d tables in %s", len(tables), args.database)

    if args.dry_run:
        for table in tables:
            print(table)
        return 0

    output_path = args.output or str(Path(args.output_dir) / f"{args.database}_table_ddl.csv")
    context = ExportContext(
        executor=executor,
        downloader=downloader,
        run_config=run_config,
        database=args.database,
    )
    try:
        export_table_ddl(context, tables, output_path, args.batch_size, args.skip_auth_check)
    except dependencies.exceptions.SsoLoginError as exc:
        _LOGGER.exception("Export aborted: %s", exc)
        return 1
    _LOGGER.info("Wrote %d table(s) DDL to %s", len(tables), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
