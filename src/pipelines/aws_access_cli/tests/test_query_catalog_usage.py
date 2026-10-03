"""Regression tests for aws_access_cli query-catalog usage."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from src.pipelines.aws_access_cli.catalog import QueryCatalog

EXPECTED_QUERY_KEYS = (
    "aws-access-cli_adoption_distinct",
    "aws-access-cli_adoption_no_vsf",
    "aws-access-cli_adoption_playback_outcome",
    "aws-access-cli_error_1xxx_session_ids",
    "aws-access-cli_incomplete_no_destroy_session_ids",
    "aws-access-cli_playback_outcome",
    "aws-access-cli_session_debug_events",
    "aws-access-cli_shaka_error_counts",
    "aws-access-cli_unique_guest_session",
)


def _docstring_nodes(module: ast.AST) -> set[ast.AST]:
    docstrings: set[ast.AST] = set()
    for parent in ast.walk(module):
        body = getattr(parent, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstrings.add(first.value)
    return docstrings


def _string_fragments(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        fragments: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                fragments.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                fragments.append("__VALUE__")
        return fragments
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return [*_string_fragments(node.left), *_string_fragments(node.right)]
    return []


def _looks_like_inline_sql(value: str) -> bool:
    normalized = " ".join(value.split()).upper()
    normalized = re.sub(r"^(?:__VALUE__\s*)+", "", normalized).lstrip(" (")
    if normalized.startswith("--") and " SELECT " in normalized:
        normalized = "SELECT " + normalized.split(" SELECT ", 1)[1]
    return bool(re.match(r"^(SELECT\b.+\bFROM\b|WITH\b.+\bSELECT\b.+\bFROM\b)", normalized))


def test_query_lookup_returns_catalog_entry() -> None:
    catalog = QueryCatalog()

    for key in EXPECTED_QUERY_KEYS:
        sql = catalog.load(key)
        assert sql.strip()
        assert "SELECT" in sql.upper() or "WITH" in sql.upper()


def test_query_lookup_unknown_key_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        QueryCatalog().load("aws-access-cli_missing_query")


def test_no_inline_sql_remains() -> None:
    source_root = Path(__file__).resolve().parents[1]
    scanned_files = 0

    for path in source_root.rglob("*.py"):
        if "tests" in path.relative_to(source_root).parts:
            continue
        scanned_files += 1
        module = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_nodes(module)
        for node in ast.walk(module):
            if node in docstrings:
                continue
            fragments = _string_fragments(node)
            if fragments:
                assert not _looks_like_inline_sql(" ".join(fragments)), f"{path}:{getattr(node, 'lineno', '?')}"
    assert scanned_files > 0


def test_inline_sql_guard_flags_commented_and_interpolated_sql() -> None:
    module = ast.parse(
        """
sql = "-- comment\\nSELECT * FROM tenant_table"
other = f"{prefix} SELECT session_id FROM {table}"
"""
    )
    assignments = [node for node in module.body if isinstance(node, ast.Assign)]
    comment_sql = " ".join(_string_fragments(assignments[0].value))
    interpolated_sql = " ".join(_string_fragments(assignments[1].value))

    assert _looks_like_inline_sql(comment_sql)
    assert _looks_like_inline_sql(interpolated_sql)
