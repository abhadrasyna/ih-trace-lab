"""`src/lib/har`'s own exception hierarchy.

`HarEntryLoader` always raises one of these on malformed input, never a bare `KeyError`/`json.JSONDecodeError`,
matching this project's "fail loudly, no silently-wrong partial results" convention.
"""
from __future__ import annotations


class HarLoaderError(Exception):
    """Base class for all `src.lib.har` errors."""


class HarFormatError(HarLoaderError):
    """Raised when a HAR document is not valid JSON, or its `log`/`log.entries` shape is malformed.

    Covers: invalid JSON, a missing/non-dict `log`, and a missing/non-list `log.entries`.
    """
