"""`CurlConverterProtocol` conformance test for the concrete `converter` implementer."""
from __future__ import annotations

from src.lib.curl_to_python.converter import CurlToRequestsConverter
from src.lib.curl_to_python.protocols import CurlConverterProtocol


def test_curl_to_requests_converter_satisfies_curl_converter_protocol() -> None:
    assert isinstance(CurlToRequestsConverter(), CurlConverterProtocol)
