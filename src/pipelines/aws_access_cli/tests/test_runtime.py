"""Tests for make_athena_client's wiring to athena_runner (runtime.py).

Only the AWS client factory and the final adapter constructor are mocked;
the executor/downloader/run_config classes are the real `athena_runner`
classes, so a constructor-signature or abstract-class mismatch against the
vendored library (not just against a mock) fails these tests.
"""
from __future__ import annotations

from dataclasses import replace
from unittest import mock

from athena_runner import query_executor, result_downloader

from src.pipelines.aws_access_cli import runtime


def test_make_athena_client_passes_profile_to_run_config() -> None:
    """RunConfig.profile must come from RuntimeConfig.profile (not omitted).

    Regression test: make_athena_client previously built RunConfig without
    a profile, which raised TypeError at call time since athena_runner's
    RunConfig.profile is a required positional field.
    """
    cfg = runtime.RuntimeConfig(profile="some-profile")
    with mock.patch("athena_runner.aws_clients.AwsClientFactory") as factory_cls, \
         mock.patch("src.lib.athena.adapter.AthenaAdapter") as adapter_cls:
        runtime.make_athena_client(cfg, database="some_db")

        factory_cls.assert_called_once_with(cfg.profile, cfg.region)
        _, kwargs = adapter_cls.call_args
        run_config = kwargs["config"]
        assert run_config.profile == cfg.profile
        assert kwargs["database"] == "some_db"


def test_make_athena_client_builds_concrete_executor_and_downloader() -> None:
    """Regression test: runtime.py must use the concrete boto-backed classes.

    `query_executor.AthenaQueryExecutor` and `result_downloader.ResultDownloader`
    are abstract base classes; instantiating them directly raises
    `TypeError: ... takes no arguments` (abc.ABC swallows __init__'s real
    signature). Only `BotoAthenaQueryExecutor`/`S3ResultDownloader` are
    constructible.
    """
    cfg = runtime.RuntimeConfig(profile="some-profile")
    with mock.patch("athena_runner.aws_clients.AwsClientFactory"), \
         mock.patch("src.lib.athena.adapter.AthenaAdapter") as adapter_cls:
        runtime.make_athena_client(cfg, database="some_db")

        _, kwargs = adapter_cls.call_args
        assert isinstance(kwargs["executor"], query_executor.BotoAthenaQueryExecutor)
        assert isinstance(kwargs["downloader"], result_downloader.S3ResultDownloader)


def test_make_athena_client_uses_runtime_config_overrides() -> None:
    """A non-default RuntimeConfig (e.g. different workgroup) still flows through."""
    cfg = replace(
        runtime.RuntimeConfig(profile="another-profile"),
        workgroup="custom-workgroup",
    )
    with mock.patch("athena_runner.aws_clients.AwsClientFactory"), \
         mock.patch("src.lib.athena.adapter.AthenaAdapter") as adapter_cls:
        runtime.make_athena_client(cfg, database="other_db")

        _, kwargs = adapter_cls.call_args
        run_config = kwargs["config"]
        assert run_config.profile == "another-profile"
        assert run_config.workgroup == "custom-workgroup"
