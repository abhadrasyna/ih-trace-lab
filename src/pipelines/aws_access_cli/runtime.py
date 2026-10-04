"""Runtime wiring for shared src/lib adapters used by the pipeline wrappers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.lib.auth.sso import SsoAuth
from src.lib.csv_io.csv_file import CsvFileWriter
from src.lib.paths.config import YamlPathResolver


@dataclass(frozen=True)
class RuntimeConfig:
    profile: str = "clarissa-insights-product"
    workgroup: str = "primary"
    output_location: str = "s3://clarissaprod-apps-athena-query-results/"
    region: str = "eu-central-1"
    poll_interval: int = 2
    timeout: int = 300
    output_dir: str = "output"
    log_dir: str = "logs"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def make_path_resolver() -> YamlPathResolver:
    return YamlPathResolver.from_file(repo_root() / "config" / "data_paths.yaml", repo_root=repo_root())


def make_csv_writer() -> CsvFileWriter:
    return CsvFileWriter()


def make_auth() -> SsoAuth:
    import boto3
    from athena_runner import aws_clients, sso_auth

    def refresher_factory(profile_name: str) -> Any:
        def sts_client_factory() -> Any:
            return aws_clients.AwsClientFactory(profile_name, None).sts_client()

        return sso_auth.SsoCredentialRefresher(profile_name, sts_client_factory)

    def session_factory(profile_name: str) -> boto3.Session:
        return boto3.Session(profile_name=profile_name)

    return SsoAuth(refresher_factory, session_factory)


def make_athena_client(runtime: RuntimeConfig, database: str) -> Any:
    from athena_runner import aws_clients, query_executor, result_downloader
    from athena_runner import config as config_lib

    from src.lib.athena.adapter import AthenaAdapter

    factory = aws_clients.AwsClientFactory(runtime.profile, runtime.region)
    run_config = config_lib.RunConfig(
        profile=runtime.profile,
        workgroup=runtime.workgroup,
        output_location=runtime.output_location,
        output_dir=runtime.output_dir,
        poll_interval_seconds=runtime.poll_interval,
        timeout_seconds=runtime.timeout,
    )
    return AthenaAdapter(
        executor=query_executor.BotoAthenaQueryExecutor(factory.athena_client(), run_config),
        downloader=result_downloader.S3ResultDownloader(factory.s3_client()),
        config=run_config,
        database=database,
    )
