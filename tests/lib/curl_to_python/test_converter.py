"""Tests for `src.lib.curl_to_python.converter`."""
from __future__ import annotations

import pytest

from src.lib.curl_to_python.converter import (
    CurlToRequestsConverter,
    UnsupportedCurlFlagError,
)


def test_convert_get_request() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert("curl -X GET https://example.com/api")

    assert "method = 'GET'" in result
    assert "url = 'https://example.com/api'" in result
    assert "response = requests.request(method, url)" in result


def test_convert_post_with_headers_and_data() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert(
        'curl https://example.com/api -H "Content-Type: application/json" -d \'{"a": 1}\''
    )

    assert "method = 'POST'" in result
    assert "headers = {'Content-Type': 'application/json'}" in result
    assert 'data = b\'{"a": 1}\'' in result
    assert "response = requests.request(method, url, headers=headers, data=data)" in result


def test_convert_does_not_execute_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conversion must never make a network call -- it only produces text."""
    import socket

    def _fail_on_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("convert() must not open a network connection")

    monkeypatch.setattr(socket.socket, "connect", _fail_on_network)

    converter = CurlToRequestsConverter()
    converter.convert("curl -X POST https://example.com/api -d 'payload'")


def test_convert_explicit_get_with_data_is_not_silently_rewritten_to_post() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert("curl -X GET https://example.com/api -d 'q=1'")

    assert "method = 'GET'" in result


def test_convert_repeated_data_flags_are_joined_with_ampersand() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert("curl https://example.com/api -d 'a=1' -d 'b=2'")

    assert "data = b'a=1&b=2'" in result


def test_convert_repeated_headers_are_merged_not_overwritten() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert(
        'curl https://example.com/api -H "Accept: text/plain" -H "Accept: application/json"'
    )

    assert "headers = {'Accept': 'text/plain, application/json'}" in result


def test_convert_data_without_explicit_content_type_gets_form_default() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert("curl https://example.com/api -d 'a=1'")

    assert "headers = {'Content-Type': 'application/x-www-form-urlencoded'}" in result


def test_convert_explicit_content_type_is_not_overridden() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert(
        'curl https://example.com/api -H "Content-Type: application/json" -d \'{"a": 1}\''
    )

    assert "headers = {'Content-Type': 'application/json'}" in result


def test_convert_repeated_cookie_headers_joined_with_semicolon() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert(
        'curl https://example.com/api -H "Cookie: a=1" -H "Cookie: b=2"'
    )

    assert "headers = {'Cookie': 'a=1; b=2'}" in result


def test_convert_non_ascii_data_is_emitted_as_utf8_bytes() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert('curl https://example.com/api -d \'{"name": "日本"}\'')

    assert "data = " + repr('{"name": "日本"}'.encode()) in result


def test_convert_header_without_colon_is_unsupported() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(UnsupportedCurlFlagError, match="unsupported curl header form"):
        converter.convert('curl https://example.com/api -H "garbage"')


def test_convert_header_remove_form_is_unsupported() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(UnsupportedCurlFlagError, match="unsupported curl header form"):
        converter.convert('curl https://example.com/api -H "Host:"')


def test_convert_header_empty_send_form_is_unsupported() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(UnsupportedCurlFlagError, match="unsupported curl header form"):
        converter.convert('curl https://example.com/api -H "X-Foo;"')


def test_convert_dollar_quote_not_at_word_start_is_not_rejected() -> None:
    converter = CurlToRequestsConverter()

    result = converter.convert("curl https://example.com/api -d 'price=5$'")

    assert "data = b'price=5$'" in result


def test_convert_ansi_c_quoting_is_unsupported() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(UnsupportedCurlFlagError, match="ANSI-C"):
        converter.convert("curl https://example.com/api -d $'a=1\\n'")


def test_convert_data_at_file_shorthand_is_unsupported() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(UnsupportedCurlFlagError, match="@file"):
        converter.convert("curl https://example.com/api -d @payload.json")


def test_convert_unsupported_flag_raises_named_error() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(UnsupportedCurlFlagError, match="-b"):
        converter.convert("curl https://example.com/api -b cookie.txt")


def test_convert_header_flag_missing_value_raises_clear_error() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(ValueError, match="requires a value"):
        converter.convert("curl https://example.com/api -H")


def test_convert_second_positional_argument_raises() -> None:
    converter = CurlToRequestsConverter()

    with pytest.raises(ValueError, match="multiple positional arguments"):
        converter.convert("curl https://example.com/api https://example.com/other")


def test_convert_multiline_curl_with_backslash_continuations() -> None:
    converter = CurlToRequestsConverter()
    curl_command = (
        "curl -X POST https://example.com/api \\\n"
        '  -H "Content-Type: application/json" \\\n'
        "  -d '{\"a\": 1}'"
    )

    result = converter.convert(curl_command)

    assert "method = 'POST'" in result
    assert "headers = {'Content-Type': 'application/json'}" in result
