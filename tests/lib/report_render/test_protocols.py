"""Tests for src.lib.report_render.protocols."""
from __future__ import annotations

from src.lib.report_render.protocols import ReportRenderer


class _ConformingRenderer:
    def render(self, rows: list[dict[str, str]]) -> str:
        return "rendered"


class _MissingRender:
    pass


def test_conforming_stub_satisfies_report_renderer_protocol() -> None:
    assert isinstance(_ConformingRenderer(), ReportRenderer)


def test_non_conforming_stub_does_not_satisfy_protocol() -> None:
    assert not isinstance(_MissingRender(), ReportRenderer)
