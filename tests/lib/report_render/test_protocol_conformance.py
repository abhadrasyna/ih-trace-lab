"""`Protocol` conformance tests for `ReportRenderer` (`functional-code-taxonomy` FCT-2).

Confirms `isinstance(..., ReportRenderer)` behaves correctly for a conforming implementer and a non-conforming
stub, per RRM-4's spec.
"""
from __future__ import annotations

from src.lib.report_render.protocols import ReportRenderer
from src.lib.report_render.writers import MarkdownTableWriter


def test_conforming_writer_satisfies_protocol() -> None:
    assert isinstance(MarkdownTableWriter(), ReportRenderer)


def test_non_conforming_stub_fails_protocol() -> None:
    class _MissingRender:
        pass

    assert not isinstance(_MissingRender(), ReportRenderer)
