"""Tests for `src.lib.auth.protocols`."""
from __future__ import annotations

import boto3

from src.lib.auth.protocols import AuthProtocol


class _ConformingStub:
    def ensure_session(self, profile_name: str) -> boto3.Session:
        return boto3.Session()

    def refresh_if_expired(self, profile_name: str) -> bool:
        return False


class _MissingRefreshIfExpired:
    def ensure_session(self, profile_name: str) -> boto3.Session:
        return boto3.Session()


def test_conforming_stub_satisfies_protocol() -> None:
    assert isinstance(_ConformingStub(), AuthProtocol)


def test_non_conforming_stub_fails_protocol() -> None:
    assert not isinstance(_MissingRefreshIfExpired(), AuthProtocol)
