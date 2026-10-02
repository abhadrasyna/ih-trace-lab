"""Tests for `src.lib.curl_to_python.protocols`."""
from __future__ import annotations

from src.lib.curl_to_python.protocols import CurlConverterProtocol


class _ConformingConverter:
    def convert(self, curl_command: str) -> str:
        return ""


class _NonConformingConverter:
    """Missing `convert` entirely — must not satisfy the Protocol."""


def test_conforming_stub_satisfies_protocol() -> None:
    assert isinstance(_ConformingConverter(), CurlConverterProtocol)


def test_non_conforming_stub_fails_protocol() -> None:
    assert not isinstance(_NonConformingConverter(), CurlConverterProtocol)
