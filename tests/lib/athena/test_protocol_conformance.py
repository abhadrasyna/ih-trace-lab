"""`AthenaClient` Protocol-conformance tests for `src.lib.athena.adapter.AthenaAdapter` -- mirrors FCT-2's own
`tests/lib/athena/test_protocols.py` conformance-test pattern (conforming vs. non-conforming stub, both via `isinstance`).
"""
from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping
from pathlib import Path

import pytest
from athena_runner import config as athena_runner_config

from src.lib.athena import adapter as adapter_module
from src.lib.athena.adapter import AthenaAdapter
from src.lib.athena.protocols import AthenaClient, QueryResult


class _FakeExecutor:
    def run(self, sql: str, database: str) -> object:  # pragma: no cover - never invoked by these conformance checks
        raise NotImplementedError


class _FakeDownloader:
    def download(self, output_location: str, destination_path: str) -> None:  # pragma: no cover - never invoked
        raise NotImplementedError


class _MissingPollStatus:
    """A stub implementing only two of `AthenaClient`'s three methods."""

    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        return "exec-123"

    def fetch_results(self, execution_id: str) -> QueryResult:
        return QueryResult(query_execution_id=execution_id, rows=[], state="SUCCEEDED")


def _make_config(tmp_path: Path) -> athena_runner_config.RunConfig:
    return athena_runner_config.RunConfig(
        profile="test-profile",
        workgroup="test-workgroup",
        output_location="s3://bucket/output/",
        output_dir=str(tmp_path),
    )


def test_adapter_satisfies_protocol(tmp_path: Path) -> None:
    adapter = AthenaAdapter(_FakeExecutor(), _FakeDownloader(), _make_config(tmp_path), database="test_db")
    assert isinstance(adapter, AthenaClient)


def test_non_conforming_stub_fails_protocol() -> None:
    assert not isinstance(_MissingPollStatus(), AthenaClient)


def test_adapter_construction_requires_collaborators() -> None:
    # Intentionally omits every required constructor argument.
    with pytest.raises(TypeError):
        AthenaAdapter()  # type: ignore[call-arg]


def test_adapter_never_calls_boto3_directly() -> None:
    """All AWS access must be delegated to the injected `athena_runner` collaborators (DIP) -- `adapter.py` itself must
    never import or reference `boto3` (only `botocore.exceptions.ClientError`, for exception typing, is permitted).

    AST-based (not a substring scan) so the module's own docstring prose mentioning "boto3" doesn't false-positive.
    """
    tree = ast.parse(inspect.getsource(adapter_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(alias.name.split(".")[0] == "boto3" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or node.module.split(".")[0] != "boto3"
        if isinstance(node, ast.Name):
            assert node.id != "boto3"
