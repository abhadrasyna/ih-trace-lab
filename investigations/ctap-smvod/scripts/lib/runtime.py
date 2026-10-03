"""Shared runtime helpers for the migrated CTAP/SM-VOD scripts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

from athena_runner.aws_clients import AwsClientFactory
from athena_runner.config import RunConfig
from athena_runner.query_executor import BotoAthenaQueryExecutor
from athena_runner.result_downloader import S3ResultDownloader
from athena_runner.sso_auth import SsoCredentialRefresher
from src.lib.athena.adapter import AthenaAdapter
from src.lib.auth.sso import SsoAuth
from src.lib.csv_io.csv_file import CsvFileWriter
from src.lib.paths import YamlPathResolver

DEFAULT_PROFILE = "clarissa-insights-product"
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


def ensure_valid_credentials(profile_name: str) -> bool:
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
