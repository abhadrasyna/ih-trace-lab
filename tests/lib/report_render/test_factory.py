"""Tests for `src/lib/report_render/factory.py`'s shape-keyed writer selection Factory Method."""
from __future__ import annotations

import pytest

from src.lib.report_render.factory import make_report_writer
from src.lib.report_render.writers import (
    CategoryBreakdownWriter,
    MarkdownTableWriter,
    StatisticalWriteupWriter,
)


def test_make_report_writer_returns_markdown_table_writer() -> None:
    assert isinstance(make_report_writer("markdown_table"), MarkdownTableWriter)


def test_make_report_writer_returns_category_breakdown_writer() -> None:
    assert isinstance(make_report_writer("category_breakdown"), CategoryBreakdownWriter)


def test_make_report_writer_returns_statistical_writeup_writer() -> None:
    assert isinstance(make_report_writer("statistical_writeup"), StatisticalWriteupWriter)


def test_make_report_writer_unknown_shape_raises() -> None:
    with pytest.raises(ValueError, match="markdown_table"):
        make_report_writer("nonsense")
