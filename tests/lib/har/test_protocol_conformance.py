"""`Protocol` conformance tests for `HarEntryLoader` (`functional-code-taxonomy` FCT-2).

Confirms `isinstance(..., HarEntryLoader)` behaves correctly for a conforming implementer
(`JsonHarEntryLoader`) and a non-conforming stub, per HLM-3's spec.
"""
from __future__ import annotations

from src.lib.har.loader import JsonHarEntryLoader
from src.lib.har.protocols import HarEntryLoader


def test_conforming_loader_satisfies_protocol() -> None:
    assert isinstance(JsonHarEntryLoader(), HarEntryLoader)


def test_non_conforming_stub_fails_protocol() -> None:
    class _MissingLoadEntries:
        pass

    assert not isinstance(_MissingLoadEntries(), HarEntryLoader)
