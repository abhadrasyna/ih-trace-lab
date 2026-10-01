#!/usr/bin/env python3
"""Harvest Athena reference markdown into deduplicated query templates."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from logs.setup_logging import setup_logging

LOGGER = logging.getLogger("scripts.dev.harvest_athena_query_catalog")

DEFAULT_SOURCES = (
    Path("/Users/abhadra/github_copilot/applauseInvestigation/investigations/queries/QUERY_CATALOG.md"),
    Path("/Users/abhadra/github_copilot/ctap-smvod-session-report/queries/QUERY_CATALOG.md"),
    Path("/Users/abhadra/github_copilot/astro-events-household-report/QUERY_CATALOG.md"),
    Path("/Users/abhadra/github_copilot/ctap-smvod-session-report/queries/athena_session_outcome.md"),
    Path("/Users/abhadra/github_copilot/ctap-smvod-session-report/queries/adoption.md"),
    Path("/Users/abhadra/github_copilot/ctap-smvod-session-report/queries/edge_4032_playback_failure.md"),
)

CLAUSE_PATTERNS = (
    re.compile(
        r"\bWHERE\b(?P<body>.*?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b|\bLIMIT\b|\bUNION\b|;|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bON\b(?P<body>.*?)(?=\b(?:WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|UNION|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN)\b|;|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bGROUP\s+BY\b(?P<body>.*?)(?=\bORDER\s+BY\b|\bHAVING\b|\bLIMIT\b|\bUNION\b|;|$)",
        re.IGNORECASE | re.DOTALL,
    ),
)
TABLE_REF_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+(?!\()(?P<table>(?:[`\"]?[A-Za-z_][\w$]*[`\"]?\.)?[`\"]?[A-Za-z_][\w$]*[`\"]?)(?:\s+(?:AS\s+)?(?P<alias>[A-Za-z_][\w$]*))?",
    re.IGNORECASE,
)
SHOW_CREATE_TABLE_RE = re.compile(
    r"\bSHOW\s+CREATE\s+TABLE\s+(?P<table>(?:[`\"]?[A-Za-z_][\w$]*[`\"]?\.)?[`\"]?[A-Za-z_][\w$]*[`\"]?)",
    re.IGNORECASE,
)
SELECT_STAR_TABLE_RE = re.compile(
    r"\bSELECT\s+\*\s+(?P<table>(?:[`\"]?[A-Za-z_][\w$]*[`\"]?\.)?[`\"]?[A-Za-z_][\w$]*[`\"]?)\s+LIMIT\b",
    re.IGNORECASE,
)
CTE_NAME_RE = re.compile(r"\bWITH\s+(?P<name>[A-Za-z_][\w$]*)\s+AS\s*\(|,\s*(?P<next_name>[A-Za-z_][\w$]*)\s+AS\s*\(", re.IGNORECASE)
DIRECT_LITERAL_RE = re.compile(
    r"(?P<lemma>(?P<expr>(?:[A-Za-z_][\w$]*\.)?[A-Za-z_][\w$]*)\s*(?P<operator>=|!=|<>|>=|<=|>|<|LIKE)\s*)(?P<literal>DATE\s+)?'[^']*'",
    re.IGNORECASE,
)
FUNCTION_LITERAL_RE = re.compile(
    r"(?P<lemma>(?P<expr>(?:json_extract_scalar|from_iso8601_timestamp|date|split_part|lower|upper|trim|substr|coalesce|max|min|sum|count)\([^)]*\)\s*(?P<operator>=|!=|<>|>=|<=|>|<|LIKE)\s*))(?P<literal>DATE\s+)?'[^']*'",
    re.IGNORECASE,
)
STATUS_SECTION_RE = re.compile(r"^##\s+Status\b(?P<body>.*?)(?=^##\s+|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE)
STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*\s*(?P<body>.+)$", re.IGNORECASE | re.MULTILINE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
NOT_YET_RUN_SIGNALS = ("not yet run", "drafted", "pending manual execution")
SQL_KEYWORDS = frozenset(
    {
        "and",
        "as",
        "asc",
        "between",
        "by",
        "case",
        "cast",
        "count",
        "cross",
        "current_date",
        "date",
        "date_diff",
        "desc",
        "distinct",
        "else",
        "end",
        "false",
        "from",
        "full",
        "group",
        "having",
        "in",
        "inner",
        "is",
        "join",
        "left",
        "like",
        "limit",
        "max",
        "min",
        "integer",
        "bigint",
        "varchar",
        "not",
        "null",
        "on",
        "or",
        "order",
        "outer",
        "right",
        "select",
        "sum",
        "then",
        "true",
        "union",
        "when",
        "where",
    }
)
FUNCTION_NAMES = frozenset(
    {
        "cast",
        "coalesce",
        "count",
        "date",
        "date_diff",
        "from_iso8601_timestamp",
        "json_extract_scalar",
        "lower",
        "max",
        "min",
        "split_part",
        "substr",
        "sum",
        "trim",
        "upper",
    }
)


@dataclass(frozen=True)
class SqlBlock:
    """A harvested SQL block plus its markdown context."""

    source_path: Path
    heading: str
    sql: str
    why: str | None
    found: str | None


@dataclass(frozen=True)
class Origin:
    """One source occurrence of a deduplicated query shape."""

    source_path: Path
    heading: str
    purpose: str
    status: str


@dataclass
class CatalogEntry:
    """Final materialized catalog entry."""

    slug: str
    shape_key: str
    tables: list[str]
    key_params: list[str]
    purpose: str
    status: str
    templated_sql: str
    origins: list[Origin] = field(default_factory=list)
    raw_query_count: int = 0


def extract_sql_blocks(markdown_path: str | Path) -> list[SqlBlock]:
    """Harvest fenced ``sql`` blocks plus their nearest heading and notes."""
    path = Path(markdown_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[SqlBlock] = []
    current_heading = path.stem
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()
        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            current_heading = _clean_inline_markdown(heading_match.group(2))

        if stripped.lower().startswith("```sql"):
            sql_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                sql_lines.append(lines[index].rstrip())
                index += 1
            sql = "\n".join(sql_lines).strip()
            why, found = _extract_following_notes(lines, index + 1)
            if sql:
                blocks.append(
                    SqlBlock(
                        source_path=path,
                        heading=current_heading,
                        sql=sql,
                        why=why,
                        found=found,
                    )
                )
        index += 1

    if not blocks:
        LOGGER.warning("No SQL blocks found in %s", path)
    return blocks


def detect_status(file_text: str) -> str:
    """Return ``drafted-not-yet-run`` when the file says so, else ``confirmed-run``."""
    status_fragments = [match.group("body") for match in STATUS_SECTION_RE.finditer(file_text)]
    status_fragments.extend(match.group("body") for match in STATUS_LINE_RE.finditer(file_text))
    if any(signal in " ".join(status_fragments).lower() for signal in NOT_YET_RUN_SIGNALS):
        return "drafted-not-yet-run"
    return "confirmed-run"


def normalize_to_shape(sql: str) -> str:
    """Reduce SQL to a dedup key based on tables plus key filter/join/group columns."""
    metadata = _shape_metadata(sql)
    table_key = ",".join(metadata["tables"])
    column_key = ",".join(metadata["columns"])
    return f"tables:{table_key}|columns:{column_key}"


def templatize(sql: str) -> str:
    """Replace quoted literals in WHERE/ON clauses with inferred placeholders."""
    templated = sql
    spans = sorted(_find_clause_spans(templated), key=lambda span: span[0], reverse=True)
    for start, end in spans:
        templated = templated[:start] + _templatize_clause(templated[start:end]) + templated[end:]
    return templated


def build_catalog(paths: Iterable[str | Path]) -> list[CatalogEntry]:
    """Harvest, deduplicate, and select a canonical template for each query shape."""
    grouped: dict[str, list[dict[str, object]]] = {}

    for raw_path in paths:
        path = Path(raw_path)
        file_text = path.read_text(encoding="utf-8")
        status = detect_status(file_text)
        blocks = extract_sql_blocks(path)
        if not blocks:
            LOGGER.warning("Skipping %s because it has no harvestable SQL blocks.", path)
            continue

        for block in blocks:
            shape_metadata = _shape_metadata(block.sql)
            shape_key = normalize_to_shape(block.sql)
            purpose = _derive_purpose(block)
            origin = Origin(
                source_path=block.source_path,
                heading=block.heading,
                purpose=purpose,
                status=status,
            )
            grouped.setdefault(shape_key, []).append(
                {
                    "origin": origin,
                    "purpose": purpose,
                    "status": status,
                    "tables": shape_metadata["tables"],
                    "columns": shape_metadata["columns"],
                    "templated_sql": templatize(block.sql),
                }
            )

    slug_counts: dict[str, int] = {}
    catalog: list[CatalogEntry] = []
    for shape_key in sorted(grouped):
        items = grouped[shape_key]
        canonical = max(items, key=_canonical_rank)
        tables = list(canonical["tables"])
        key_params = _extract_placeholders(str(canonical["templated_sql"])) or list(canonical["columns"])
        slug = _unique_slug(_make_slug(tables, list(canonical["columns"])), slug_counts)
        purpose = str(canonical["purpose"])
        status = "confirmed-run" if any(str(item["status"]) == "confirmed-run" for item in items) else "drafted-not-yet-run"
        origins = sorted({item["origin"] for item in items}, key=lambda origin: (_display_source(origin.source_path), origin.heading))

        catalog.append(
            CatalogEntry(
                slug=slug,
                shape_key=shape_key,
                tables=tables,
                key_params=key_params,
                purpose=purpose,
                status=status,
                templated_sql=str(canonical["templated_sql"]).strip(),
                origins=origins,
                raw_query_count=len(items),
            )
        )

    return catalog


def write_catalog(root: str | Path, catalog: Iterable[CatalogEntry]) -> None:
    """Write ``queries/athena/*.sql`` plus ``queries/athena/index.md``."""
    root_path = Path(root).resolve()
    output_dir = root_path / "queries" / "athena"
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = sorted(catalog, key=lambda entry: entry.slug)
    desired_files = {f"{entry.slug}.sql" for entry in entries}
    for existing_sql in output_dir.glob("*.sql"):
        if existing_sql.name not in desired_files:
            existing_sql.unlink()

    for entry in entries:
        sql_path = output_dir / f"{entry.slug}.sql"
        sql_path.write_text(_render_sql_file(entry), encoding="utf-8")

    index_path = output_dir / "index.md"
    index_path.write_text(_render_index(entries), encoding="utf-8")


def main() -> None:
    """Run the harvest pipeline from markdown sources to ``queries/athena/``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        type=Path,
        nargs="+",
        default=list(DEFAULT_SOURCES),
        help="One or more markdown files to harvest (default: the 6 reference files).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to write queries/athena into (default: this repo root).",
    )
    args = parser.parse_args()

    setup_logging()
    catalog = build_catalog(args.sources)
    write_catalog(args.root, catalog)

    total_raw_queries = sum(entry.raw_query_count for entry in catalog)
    print(f"Wrote {len(catalog)} Athena query shapes from {total_raw_queries} raw SQL blocks.")
    for entry in sorted(catalog, key=lambda item: item.slug):
        print(f"  {entry.slug}: {entry.raw_query_count} raw quer{'y' if entry.raw_query_count == 1 else 'ies'}")


def _canonical_rank(item: dict[str, object]) -> tuple[int, int, int]:
    templated_sql = str(item["templated_sql"])
    status_score = 1 if str(item["status"]) == "confirmed-run" else 0
    placeholder_score = len(_extract_placeholders(templated_sql))
    return status_score, placeholder_score, len(templated_sql)


def _clean_inline_markdown(text: str) -> str:
    return " ".join(text.replace("`", "").split())


def _derive_purpose(block: SqlBlock) -> str:
    source_text = block.why or block.heading
    return _clean_inline_markdown(_strip_labeled_prefix(source_text))


def _extract_following_notes(lines: list[str], start_index: int) -> tuple[str | None, str | None]:
    why: str | None = None
    found: str | None = None
    index = start_index

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```") or HEADING_RE.match(stripped):
            break
        if stripped.startswith("**Why"):
            why, index = _consume_labeled_note(lines, index)
            continue
        if stripped.startswith("**Found"):
            found, index = _consume_labeled_note(lines, index)
            continue
        break
    return why, found


def _consume_labeled_note(lines: list[str], start_index: int) -> tuple[str, int]:
    captured: list[str] = [lines[start_index].strip()]
    index = start_index + 1

    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("```") or HEADING_RE.match(stripped):
            break
        if stripped.startswith("**Why") or stripped.startswith("**Found"):
            break
        if not stripped:
            next_nonblank = _next_nonblank_line(lines, index + 1)
            if next_nonblank is None or next_nonblank.startswith("```") or HEADING_RE.match(next_nonblank) or next_nonblank.startswith(("**Why", "**Found")):
                break
            captured.append("")
            index += 1
            continue
        captured.append(lines[index].rstrip())
        index += 1

    cleaned = _strip_labeled_prefix("\n".join(captured))
    return cleaned.strip(), index


def _next_nonblank_line(lines: list[str], start_index: int) -> str | None:
    for index in range(start_index, len(lines)):
        stripped = lines[index].strip()
        if stripped:
            return stripped
    return None


def _strip_labeled_prefix(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^\*\*(Why|Found)\b.*?\*\*\s*", "", stripped, count=1, flags=re.IGNORECASE | re.DOTALL)
    return stripped


def _shape_metadata(sql: str) -> dict[str, list[str]]:
    stripped_sql = _strip_sql_comments(sql)
    tables, aliases = _extract_tables_and_aliases(stripped_sql)
    columns: set[str] = set()
    for clause in _extract_clause_bodies(stripped_sql):
        columns.update(_extract_clause_columns(clause, aliases, tables))
    return {"tables": tables, "columns": sorted(columns)}


def _strip_sql_comments(sql: str) -> str:
    return re.sub(r"--.*$", "", sql, flags=re.MULTILINE)


def _extract_tables_and_aliases(sql: str) -> tuple[list[str], set[str]]:
    seen_tables: list[str] = []
    aliases: set[str] = set()
    cte_names = _extract_cte_names(sql)

    for match in TABLE_REF_RE.finditer(sql):
        table_name = _normalize_table_name(match.group("table"))
        bare_name = table_name.split(".")[-1]
        if bare_name in cte_names:
            continue
        if table_name not in seen_tables:
            seen_tables.append(table_name)
        alias = match.group("alias")
        if alias and alias.upper() not in {"ON", "USING", "WHERE", "GROUP", "ORDER", "LEFT", "RIGHT", "INNER", "FULL", "CROSS", "JOIN"}:
            aliases.add(alias.lower())

    if not seen_tables:
        show_create_matches = [_normalize_table_name(match.group("table")) for match in SHOW_CREATE_TABLE_RE.finditer(sql)]
        if show_create_matches:
            seen_tables.extend(table for table in show_create_matches if table not in seen_tables)
        else:
            match = SELECT_STAR_TABLE_RE.search(sql)
            if match:
                seen_tables.append(_normalize_table_name(match.group("table")))

    return seen_tables, aliases


def _normalize_table_name(raw_name: str) -> str:
    return raw_name.replace('"', "").replace("`", "").strip().lower()


def _extract_cte_names(sql: str) -> set[str]:
    cte_names: set[str] = set()
    for match in CTE_NAME_RE.finditer(sql):
        if match.group("name"):
            cte_names.add(match.group("name").lower())
        if match.group("next_name"):
            cte_names.add(match.group("next_name").lower())
    return cte_names


def _extract_clause_bodies(sql: str) -> list[str]:
    return [match.group("body") for pattern in CLAUSE_PATTERNS for match in pattern.finditer(sql)]


def _extract_clause_columns(clause: str, aliases: set[str], tables: list[str]) -> set[str]:
    clause_without_literals = re.sub(r"'[^']*'", "''", clause)
    table_parts = {part for table in tables for part in table.split(".")}
    columns: set[str] = set()

    for token_match in re.finditer(r"\b(?:[A-Za-z_][\w$]*\.)?([A-Za-z_][\w$]*)\b", clause_without_literals):
        token = token_match.group(1).lower()
        if token in SQL_KEYWORDS or token in FUNCTION_NAMES or token in aliases or token in table_parts:
            continue

        full_match = token_match.group(0)
        if "." in full_match and full_match.split(".", 1)[0].lower() in aliases:
            columns.add(token)
            continue

        following = clause_without_literals[token_match.end() : token_match.end() + 1]
        if following == "(":
            continue

        columns.add(token)

    return columns


def _find_clause_spans(sql: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in CLAUSE_PATTERNS[:2]:
        for match in pattern.finditer(sql):
            spans.append(match.span("body"))
    return spans


def _templatize_clause(clause: str) -> str:
    templated = DIRECT_LITERAL_RE.sub(_replace_literal_comparison, clause)
    templated = FUNCTION_LITERAL_RE.sub(_replace_literal_comparison, templated)
    return templated


def _replace_literal_comparison(match: re.Match[str]) -> str:
    expression = match.group("expr")
    operator = match.group("operator")
    placeholder_base = _placeholder_name_from_expression(expression)
    if operator.upper() == "LIKE":
        placeholder_base = f"{placeholder_base}_pattern"
    elif operator in {">", ">="}:
        placeholder_base = f"{placeholder_base}_start"
    elif operator in {"<", "<="}:
        placeholder_base = f"{placeholder_base}_end"
    return f"{match.group('lemma')}{{{{{placeholder_base}}}}}"


def _placeholder_name_from_expression(expression: str) -> str:
    json_path_name = _extract_json_path_name(expression)
    if json_path_name is not None:
        return json_path_name
    expression_without_strings = re.sub(r"'[^']*'", "", expression)
    tokens = [
        token.lower()
        for token in re.findall(r"\b(?:[A-Za-z_][\w$]*\.)?([A-Za-z_][\w$]*)\b", expression_without_strings)
        if token.lower() not in SQL_KEYWORDS and token.lower() not in FUNCTION_NAMES
    ]
    if not tokens:
        return "value"
    return _snake_case(tokens[-1])


def _extract_json_path_name(expression: str) -> str | None:
    match = re.search(r"\$\.(?P<name>[A-Za-z_][\w$]*)", expression)
    if match is None:
        return None
    return _snake_case(match.group("name"))


def _snake_case(value: str) -> str:
    collapsed = re.sub(r"[^A-Za-z0-9]+", "_", value)
    collapsed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", collapsed)
    return collapsed.strip("_").lower() or "value"


def _extract_placeholders(sql: str) -> list[str]:
    return sorted(set(re.findall(r"\{\{([a-z0-9_]+)\}\}", sql)))


def _make_slug(tables: list[str], columns: list[str]) -> str:
    table_bits = [_snake_case(table.split(".")[-1]) for table in tables[:2]]
    column_bits = [_snake_case(column) for column in columns[:4]]
    base_parts = [*table_bits, *column_bits]
    base_parts = [part for part in base_parts if part]
    return _slugify("-".join(base_parts) or "athena-query")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "athena-query"


def _unique_slug(base_slug: str, slug_counts: dict[str, int]) -> str:
    count = slug_counts.get(base_slug, 0) + 1
    slug_counts[base_slug] = count
    return base_slug if count == 1 else f"{base_slug}-{count}"


def _render_sql_file(entry: CatalogEntry) -> str:
    params = ", ".join(f"`{param}`" for param in entry.key_params) if entry.key_params else "—"
    tables = ", ".join(f"`{table}`" for table in entry.tables) if entry.tables else "—"
    sources = "\n".join(f"--   - {_display_source(origin.source_path)} :: {origin.heading}" for origin in entry.origins)
    return (
        f"-- Purpose: {entry.purpose}\n"
        f"-- Tables: {tables}\n"
        f"-- Params: {params}\n"
        f"-- Status: {entry.status}\n"
        "-- Source:\n"
        f"{sources}\n\n"
        f"{entry.templated_sql.strip()}\n"
    )


def _render_index(entries: list[CatalogEntry]) -> str:
    lines = [
        "# Athena query catalog",
        "",
        "Auto-generated by `scripts/dev/harvest_athena_query_catalog.py` — regenerate it from the source catalogs instead of hand-editing.",
        "",
        "| Slug | Tables | Key params | Purpose | Status | Source |",
        "|---|---|---|---|---|---|",
    ]
    for entry in entries:
        tables = "<br>".join(f"`{_escape_table(table)}`" for table in entry.tables) or "—"
        params = "<br>".join(f"`{_escape_table(param)}`" for param in entry.key_params) or "—"
        sources = "<br>".join(
            f"`{_escape_table(_display_source(origin.source_path))}` :: {_escape_table(origin.heading)}"
            for origin in entry.origins
        )
        lines.append("<!-- lint-ignore-length -->")
        lines.append(
            f"| `{entry.slug}` | {tables} | {params} | {_escape_table(entry.purpose)} | {entry.status} | {sources} |"
        )
    lines.append("")
    return "\n".join(lines)


def _display_source(path: Path) -> str:
    marker = "github_copilot/"
    rendered = str(path)
    if marker in rendered:
        return rendered.split(marker, 1)[1]
    return rendered


def _escape_table(text: str) -> str:
    return text.replace("|", r"\|")


if __name__ == "__main__":
    main()
