#!/usr/bin/env python3
"""CLI: scan a reference repository's Python files and write a high-level
Mermaid overview diagram + per-project file-count table to a markdown file.

Read-only against the scanned source tree; only the --out file is written.

Usage:
    python3 scripts/reference_diagram/main.py \\
        --source /Users/abhadra/github_copilot \\
        --out docs/reference-architecture.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reference_diagram.lib import discover_projects, link_cross_project_imports, render_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Root of the reference repo to scan (e.g. /Users/abhadra/github_copilot)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Markdown file to write the report + Mermaid diagram to",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_dir():
        parser.error(f"--source {source} is not a directory")

    projects = discover_projects(source)
    link_cross_project_imports(projects)
    report = render_report(projects, source)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Wrote {args.out} ({len(projects)} projects)")


if __name__ == "__main__":
    main()
