"""Tests for src.lib.report_render.writers."""
from __future__ import annotations

import pytest

from src.lib.report_render.writers import (
    CategoryBreakdownWriter,
    MarkdownTableWriter,
    StatisticalWriteupWriter,
)


def test_markdown_table_writer_renders_expected_rows() -> None:
    rows = [
        {"event": "manifest", "time_ms": "120"},
        {"event": "first_frame", "time_ms": "840"},
    ]
    rendered = MarkdownTableWriter().render(rows)
    assert rendered == (
        "| event | time_ms |\n"
        "| --- | --- |\n"
        "| manifest | 120 |\n"
        "| first_frame | 840 |\n"
    )


def test_markdown_table_writer_handles_empty_rows() -> None:
    assert MarkdownTableWriter().render([]) == "_No rows to report._\n"


def test_category_breakdown_writer_includes_counts_and_top_n() -> None:
    rows = [{"category": "buffering"}] * 3 + [{"category": "startup"}] * 2 + [{"category": "seek"}] * 1
    rendered = CategoryBreakdownWriter(top_n=2).render(rows)
    assert "## Category Breakdown" in rendered
    assert "| buffering | 3 |" in rendered
    assert "| startup | 2 |" in rendered
    assert "### Top 2" in rendered
    assert "1. buffering (3)" in rendered
    assert "2. startup (2)" in rendered
    assert "seek" not in rendered.split("### Top 2")[1]


def test_category_breakdown_writer_groups_missing_category_as_uncategorized() -> None:
    rendered = CategoryBreakdownWriter().render([{"other": "x"}])
    assert "(uncategorized)" in rendered


def test_category_breakdown_writer_groups_none_category_as_uncategorized() -> None:
    rendered = CategoryBreakdownWriter().render([{"category": None}, {"category": "x"}])
    assert "(uncategorized)" in rendered


def test_markdown_table_writer_escapes_pipes_and_newlines() -> None:
    rows = [{"event": "a|b", "note": "line1\nline2"}]
    rendered = MarkdownTableWriter().render(rows)
    assert "a\\|b" in rendered
    assert "line1 line2" in rendered
    assert len(rendered.splitlines()) == 3


def test_category_breakdown_writer_top_n_matches_table_tie_order() -> None:
    rendered = CategoryBreakdownWriter(top_n=1).render([{"category": "b"}, {"category": "a"}])
    table_section, top_section = rendered.split("### Top 1")
    data_rows = [line for line in table_section.splitlines() if line.startswith("| ")][2:]
    assert "1. a (1)" in top_section
    assert data_rows[0] == "| a | 1 |"


def test_category_breakdown_writer_rejects_negative_top_n() -> None:
    with pytest.raises(ValueError, match="top_n"):
        CategoryBreakdownWriter(top_n=-1)


def test_markdown_table_writer_unions_columns_across_rows() -> None:
    rows = [{"event": "a"}, {"event": "b", "error": "timeout"}]
    rendered = MarkdownTableWriter().render(rows)
    assert "| event | error |" in rendered
    assert "| a |  |" in rendered
    assert "| b | timeout |" in rendered


def test_markdown_table_writer_escapes_backslash_before_pipe() -> None:
    rendered = MarkdownTableWriter().render([{"regex": "a\\|b"}])
    assert "a\\\\\\|b" in rendered


def test_category_breakdown_writer_top_n_heading_matches_shown_count() -> None:
    rendered = CategoryBreakdownWriter(top_n=5).render([{"category": "a"}, {"category": "b"}])
    assert "### Top 2" in rendered


def test_markdown_table_writer_escapes_header_cells() -> None:
    rendered = MarkdownTableWriter().render([{"a|b": "x"}])
    assert "a\\|b" in rendered.splitlines()[0]


def test_statistical_writeup_writer_detects_high_outlier_in_small_sample() -> None:
    rows = [{"value": "10"}, {"value": "10"}, {"value": "10"}, {"value": "10"}, {"value": "1000"}]
    rendered = StatisticalWriteupWriter().render(rows)
    assert "1 row(s) outside" in rendered


def test_statistical_writeup_writer_detects_low_outlier_in_small_sample() -> None:
    rows = [{"value": "10"}, {"value": "10"}, {"value": "10"}, {"value": "10"}, {"value": "-1000"}]
    rendered = StatisticalWriteupWriter().render(rows)
    assert "1 row(s) outside" in rendered


def test_statistical_writeup_writer_outlier_list_items_are_escaped() -> None:
    rows = [{"value": "10"}, {"value": "10"}, {"value": "10"}, {"value": "10"}, {"value": "1000", "note": "a|b"}]
    rendered = StatisticalWriteupWriter().render(rows)
    assert "a\\|b" in rendered


def test_statistical_writeup_writer_rejects_nan_and_inf_values() -> None:
    rows = [{"value": "nan"}, {"value": "inf"}, {"value": "-inf"}]
    rendered = StatisticalWriteupWriter().render(rows)
    assert "No numeric `value` data." in rendered


def test_statistical_writeup_writer_includes_all_sections() -> None:
    rows = [
        {"value": "10", "buffering_ms": "100", "startup_ms": "500", "category": "a", "anomaly": "false"},
        {"value": "11", "buffering_ms": "110", "startup_ms": "510", "category": "b", "anomaly": "false"},
        {"value": "9", "buffering_ms": "90", "startup_ms": "490", "category": "a", "anomaly": "false"},
        {"value": "12", "buffering_ms": "120", "startup_ms": "520", "category": "b", "anomaly": "false"},
        {"value": "10", "buffering_ms": "100", "startup_ms": "500", "category": "a", "anomaly": "false"},
        {"value": "500", "buffering_ms": "9000", "startup_ms": "9500", "category": "a", "anomaly": "true"},
    ]
    rendered = StatisticalWriteupWriter().render(rows)
    assert "## Distribution" in rendered
    assert "## Buffering / Startup Stats" in rendered
    assert "## Outliers" in rendered
    assert "## Breakdown" in rendered
    assert "## Anomaly Scan" in rendered
    assert "1 row(s) outside" in rendered
    assert "1 row(s) flagged" in rendered


def test_statistical_writeup_writer_handles_missing_keys_gracefully() -> None:
    rendered = StatisticalWriteupWriter().render([{"unrelated": "x"}])
    assert "No numeric `value` data." in rendered
    assert "no data" in rendered
    assert "Not enough `value` data" in rendered
    assert "None detected." in rendered
