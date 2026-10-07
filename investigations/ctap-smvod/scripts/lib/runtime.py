"""Shared runtime helpers for the migrated CTAP/SM-VOD scripts."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter
from src.lib.csv_io.existing_output import csv_has_data
from src.lib.paths import YamlPathResolver

DEFAULT_PROFILE = "clarissa-insights-product"
INVESTIGATION_SLUG = "ctap-smvod"
_DEFAULT_OUTPUT_LOCATION = "s3://clarissaprod-apps-athena-query-results/"
_DEFAULT_WORKGROUP = "primary"
_DEFAULT_REGION = "eu-central-1"
_DEFAULT_TIMEOUT = 300
_DEFAULT_POLL_INTERVAL = 2


@dataclass(frozen=True)
class AthenaRunResult:
    execution_id: str
    row_count: int
    output_path: Path


def repo_root() -> Path:
    return REPO_ROOT


def make_path_resolver() -> YamlPathResolver:
    return YamlPathResolver.from_file(REPO_ROOT / "config" / "data_paths.yaml", repo_root=REPO_ROOT)


def ddmmyyyy_to_date(raw_date: str) -> date:
    return datetime.strptime(raw_date, "%d%m%Y").date()


def ddmmyyyy_to_iso(raw_date: str) -> str:
    return ddmmyyyy_to_date(raw_date).isoformat()


def investigation_output_dir(output_dir: str | Path | None = None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    return make_path_resolver().resolve_investigation_output_dir(INVESTIGATION_SLUG)


def snapshot_output_path(date_ddmmyyyy: str, artifact: str, *, output_dir: str | Path | None = None) -> str:
    resolver = make_path_resolver()
    return str(investigation_output_dir(output_dir) / resolver.format_snapshot_filename(ddmmyyyy_to_date(date_ddmmyyyy), artifact))


def range_output_path(
    start_ddmmyyyy: str,
    end_ddmmyyyy: str,
    artifact: str,
    *,
    tag: str | None = None,
    output_dir: str | Path | None = None,
) -> str:
    resolver = make_path_resolver()
    return str(
        investigation_output_dir(output_dir)
        / resolver.format_range_filename(ddmmyyyy_to_date(start_ddmmyyyy), ddmmyyyy_to_date(end_ddmmyyyy), artifact, tag=tag)
    )


def rollup_output_path(artifact: str, *, output_dir: str | Path | None = None) -> str:
    resolver = make_path_resolver()
    return str(investigation_output_dir(output_dir) / resolver.format_rollup_filename(artifact))


def ensure_valid_credentials(profile_name: str) -> bool:
    from athena_runner.aws_clients import AwsClientFactory
    from athena_runner.sso_auth import SsoCredentialRefresher
    from src.lib.auth.sso import SsoAuth

    auth = SsoAuth(
        refresher_factory=lambda profile: SsoCredentialRefresher(
            profile=profile,
            sts_client_factory=lambda: AwsClientFactory(profile, region=_DEFAULT_REGION).sts_client(),
        ),
        session_factory=lambda profile: AwsClientFactory(profile, region=_DEFAULT_REGION)._session,
    )
    refreshed = auth.refresh_if_expired(profile_name)
    return not refreshed


def make_athena_adapter(
    *,
    profile: str,
    region: str = _DEFAULT_REGION,
    workgroup: str = _DEFAULT_WORKGROUP,
    output_location: str = _DEFAULT_OUTPUT_LOCATION,
    output_dir: str,
    poll_interval: int = _DEFAULT_POLL_INTERVAL,
    timeout: int = _DEFAULT_TIMEOUT,
    database: str,
) -> AthenaAdapter:
    from athena_runner.aws_clients import AwsClientFactory
    from athena_runner.config import RunConfig
    from athena_runner.query_executor import BotoAthenaQueryExecutor
    from athena_runner.result_downloader import S3ResultDownloader
    from src.lib.athena.adapter import AthenaAdapter

    factory = AwsClientFactory(profile, region=region)
    run_config = RunConfig(
        profile=profile,
        workgroup=workgroup,
        output_location=output_location,
        output_dir=output_dir,
        region=region,
        poll_interval_seconds=poll_interval,
        timeout_seconds=timeout,
    )
    return AthenaAdapter(
        BotoAthenaQueryExecutor(factory.athena_client(), run_config),
        S3ResultDownloader(factory.s3_client()),
        run_config,
        database=database,
    )


def should_skip_athena(output_path: str, *, force: bool) -> bool:
    """True (after printing why) when `output_path` already has data and --force wasn't given."""
    if force or not csv_has_data(CsvFileReader(), Path(output_path)):
        return False
    print(f"SKIP: {output_path} already has data; use --force to re-run Athena.", file=sys.stderr)
    return True


def run_athena_query(
    *,
    sql: str,
    params: dict[str, str],
    output_path: str,
    profile: str = DEFAULT_PROFILE,
    database: str,
    workgroup: str = _DEFAULT_WORKGROUP,
    output_location: str = _DEFAULT_OUTPUT_LOCATION,
    region: str = _DEFAULT_REGION,
    poll_interval: int = _DEFAULT_POLL_INTERVAL,
    timeout: int = _DEFAULT_TIMEOUT,
) -> AthenaRunResult:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    adapter = make_athena_adapter(
        profile=profile,
        region=region,
        workgroup=workgroup,
        output_location=output_location,
        output_dir=str(target.parent),
        poll_interval=poll_interval,
        timeout=timeout,
        database=database,
    )
    execution_id = adapter.start_query(sql, params)
    result = adapter.fetch_results(execution_id)
    fieldnames = list(result.rows[0].keys()) if result.rows else []
    CsvFileWriter().write_rows(str(target), result.rows, fieldnames)
    return AthenaRunResult(execution_id=execution_id, row_count=len(result.rows), output_path=target)
