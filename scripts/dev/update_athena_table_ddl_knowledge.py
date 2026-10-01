#!/usr/bin/env python3
"""Update a knowledge markdown file's DDL section from a table-DDL CSV.

Pairs with ``scripts/athena/run_table_ddl_export.py``, which produces the CSV this script reads (columns:
``table_name``, ``ddl``). This script only does the CSV-to-markdown rendering step, so it composes with that export
step instead of duplicating Athena-querying logic.

The DDL section is delimited by fixed marker comments so re-running this script after a future re-export replaces just
that section in place, without disturbing hand-written notes elsewhere in the file.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Sequence

_SECTION_BEGIN = "<!-- DDL_SECTION:BEGIN -->"
_SECTION_END = "<!-- DDL_SECTION:END -->"


def parse_ddl_csv(csv_path: str) -> list[tuple[str, str]]:
    """Read ``csv_path`` and return ``(table_name, ddl)`` pairs in input order."""

    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"table_name", "ddl"}.issubset(reader.fieldnames):
            raise ValueError(f"{csv_path} must have 'table_name' and 'ddl' columns, got {reader.fieldnames}")
        return [(row["table_name"], row["ddl"]) for row in reader]


def render_ddl_section(rows: list[tuple[str, str]]) -> str:
    """Render ``rows`` as a markdown section, sorted by table name."""

    lines = [_SECTION_BEGIN, "", "## DDL reference", ""]
    for table_name, ddl in sorted(rows, key=lambda row: row[0]):
        lines.extend([f"### `{table_name}`", "", "```sql", ddl.rstrip("\n"), "```", ""])
    lines.append(_SECTION_END)
    return "\n".join(lines)


def update_markdown(markdown_path: str, ddl_section: str) -> None:
    """Replace or append ``ddl_section`` in the file at ``markdown_path``."""

    markdown = Path(markdown_path)
    content = markdown.read_text(encoding="utf-8")

    has_begin = _SECTION_BEGIN in content
    has_end = _SECTION_END in content
    if has_begin != has_end:
        raise ValueError(
            f"{markdown_path} has an unmatched DDL section marker -- expected both or neither of BEGIN/END."
        )

    if has_begin:
        begin_index = content.index(_SECTION_BEGIN)
        end_index = content.index(_SECTION_END) + len(_SECTION_END)
        new_content = content[:begin_index] + ddl_section + content[end_index:]
    else:
        separator = "" if content.endswith("\n\n") else ("\n" if content.endswith("\n") else "\n\n")
        new_content = content + separator + ddl_section + "\n"

    markdown.write_text(new_content, encoding="utf-8")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the knowledge-markdown updater."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to the table-DDL CSV (table_name, ddl columns).")
    parser.add_argument("--markdown", required=True, help="Path to the knowledge markdown file to update.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Read the DDL CSV and update the knowledge markdown's DDL section."""

    args = _parse_args(argv)
    rows = parse_ddl_csv(args.csv)
    ddl_section = render_ddl_section(rows)
    update_markdown(args.markdown, ddl_section)
    print(f"Updated {args.markdown} with DDL for {len(rows)} table(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
