"""Concrete `CurlConverterProtocol` implementer: curl command text -> Python `requests` source text.

Per this story's locked-in decisions (`docs/plan/src-lib-migration/curl-to-python-lib-migration/prompt.md`):
- Supported curl grammar is method, URL, headers, data only. Any other flag raises
  `UnsupportedCurlFlagError` naming the flag -- never silently dropped.
- Sensitive headers/tokens are preserved as-is in generated code (no redaction): the output is a
  local investigation script, not shipped/exported code, and redaction would silently produce
  broken (unusable) output.
- Output targets the `requests` library only; no `httpx` output path.

Text/AST generation only: this module never executes the converted request (no `exec`/`eval`, no
network call made during conversion). See CPM-1's finding in this story's `stories.md` for why no
existing `github_copilot` file is being ported from -- this implementer is built directly from the
locked-in grammar spec above.

**Known limitation (documented, not silently wrong):** backslash-newline line continuations
*inside* a quoted header/data value are not distinguished from continuations *between* flags
(curl's real, devtools-observed continuation pattern is one flag per line, which this module
supports correctly). Properly tracking shell quote state across continuations is out of scope for
this grammar-limited converter; extend only when a real consumer hits this case.
"""
from __future__ import annotations

import re
import shlex

_ANSI_C_QUOTE = re.compile(r"(?:^|\s)\$'")

_METHOD_FLAGS = ("-X", "--request")
_HEADER_FLAGS = ("-H", "--header")
# `@file` is a curl shorthand for "read the body from this file" on `-d`/`--data`/`--data-binary`
# (but *not* on `--data-raw`, which curl documents as disabling the `@` special meaning). This
# converter never touches the filesystem, so an `@`-prefixed value on those three flags is treated
# as an unsupported flag value rather than emitted as a literal (and wrong) string body.
_DATA_FLAGS_HONORING_AT = ("-d", "--data", "--data-binary")
_DATA_FLAGS = _DATA_FLAGS_HONORING_AT + ("--data-raw",)
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


class UnsupportedCurlFlagError(ValueError):
    """Raised when a curl command uses a flag/value/quoting style outside the supported grammar."""


class CurlToRequestsConverter:
    """`CurlConverterProtocol` implementer producing `requests.request(...)` call text."""

    def convert(self, curl_command: str) -> str:
        tokens = self._tokenize(curl_command)
        method, url, headers, data_parts = self._parse(tokens)
        data = "&".join(data_parts) if data_parts else None
        return self._render(method, url, headers, data)

    def _tokenize(self, curl_command: str) -> list[str]:
        # Collapse shell-style `\<newline>` (and `\<CRLF>`) line continuations before tokenizing --
        # shlex treats a lone backslash-newline as an escaped literal newline, not a continuation,
        # so multiline curl commands (copied as-is from browser devtools) would otherwise leave
        # stray newline/carriage-return tokens in the parsed argument list.
        normalized = curl_command.replace("\\\r\n", " ").replace("\\\n", " ")
        if _ANSI_C_QUOTE.search(normalized):
            raise UnsupportedCurlFlagError(
                "unsupported curl quoting: $'...' (ANSI-C quoting) is not supported"
            )
        tokens = shlex.split(normalized)
        if not tokens or tokens[0] != "curl":
            raise ValueError("expected a curl command starting with 'curl'")
        return tokens[1:]

    def _parse(self, tokens: list[str]) -> tuple[str, str, dict[str, str], list[str]]:
        method = "GET"
        method_explicit = False
        url: str | None = None
        # Headers are tracked by lowercased name so repeated headers (same name, possibly
        # differing only in case) merge per HTTP's documented combining rule instead of the later
        # one silently overwriting the earlier. `Cookie` is joined with "; " (its own documented
        # separator); every other header is joined with ", ".
        header_order: list[str] = []
        header_values: dict[str, list[str]] = {}
        header_original_name: dict[str, str] = {}
        data_parts: list[str] = []

        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token in _METHOD_FLAGS:
                index = self._require_value(tokens, index, token)
                method = tokens[index]
                method_explicit = True
            elif token in _HEADER_FLAGS:
                index = self._require_value(tokens, index, token)
                header_text = tokens[index]
                name, colon_found, value = header_text.partition(":")
                name = name.strip()
                value = value.strip()
                # curl gives special meaning to headers without a plain "Name: value" shape:
                # `-H "Host:"` (empty value) means "remove this header" and `-H "X-Foo;"` (name
                # ending in `;`, no colon) means "send an empty header" -- neither is a value this
                # converter can express since it never starts from an existing header set to
                # remove from. Fail loudly rather than emitting a wrong/misnamed header.
                if not colon_found or not name or not value or name.endswith(";"):
                    raise UnsupportedCurlFlagError(
                        f"unsupported curl header form: {header_text!r} "
                        "(only plain 'Name: value' headers are supported)"
                    )
                key = name.lower()
                if key not in header_values:
                    header_order.append(key)
                    header_values[key] = []
                    header_original_name[key] = name
                header_values[key].append(value)
            elif token in _DATA_FLAGS:
                index = self._require_value(tokens, index, token)
                value = tokens[index]
                if token in _DATA_FLAGS_HONORING_AT and value.startswith("@"):
                    raise UnsupportedCurlFlagError(
                        f"unsupported curl data flag value: {token} {value} (@file reads are not supported)"
                    )
                data_parts.append(value)
                if not method_explicit:
                    method = "POST"
            elif token.startswith("-"):
                raise UnsupportedCurlFlagError(f"unsupported curl flag: {token}")
            else:
                if url is not None:
                    raise ValueError(
                        f"multiple positional arguments found; expected exactly one URL, got a second: {token!r}"
                    )
                url = token
            index += 1

        if url is None:
            raise ValueError("no URL found in curl command")

        headers: dict[str, str] = {}
        for key in header_order:
            separator = "; " if key == "cookie" else ", "
            headers[header_original_name[key]] = separator.join(header_values[key])

        # curl's own documented default: a `-d`/`--data*` body with no explicit Content-Type
        # header gets `application/x-www-form-urlencoded`. Match that default rather than silently
        # sending no Content-Type (an explicit `-H "Content-Type: ..."` always wins, since it is
        # inserted above before this check runs).
        if data_parts and not any(name.lower() == "content-type" for name in headers):
            headers["Content-Type"] = _FORM_CONTENT_TYPE

        return method, url, headers, data_parts

    def _require_value(self, tokens: list[str], index: int, flag: str) -> int:
        next_index = index + 1
        if next_index >= len(tokens):
            raise ValueError(f"curl flag {flag!r} requires a value but none was given")
        return next_index

    def _render(self, method: str, url: str, headers: dict[str, str], data: str | None) -> str:
        lines = ["import requests", "", f"method = {method!r}", f"url = {url!r}"]
        call_args = ["method", "url"]

        if headers:
            lines.append(f"headers = {headers!r}")
            call_args.append("headers=headers")
        if data is not None:
            # Encoded as UTF-8 bytes (matching curl's own byte-for-byte payload behavior) rather
            # than a `str`, so non-ASCII bodies don't hit `requests`'/`http.client`'s Latin-1
            # str-body encoding at send time.
            lines.append(f"data = {data.encode('utf-8')!r}")
            call_args.append("data=data")

        lines.append(f"response = requests.request({', '.join(call_args)})")
        return "\n".join(lines) + "\n"
