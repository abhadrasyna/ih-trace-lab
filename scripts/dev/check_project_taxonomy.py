#!/usr/bin/env python3
"""List top-level directories that do not match the project taxonomy."""
from __future__ import annotations

import argparse
from pathlib import Path

CATEGORY_MARKERS: dict[str, tuple[str, ...]] = {
    "investigation": ("docs", "scripts", "tests"),
    "tool": ("src", "tests", "README.md"),
    "pipeline": ("scripts", "tests", "README.md"),
    "experiment": ("README.md",),
}
DEFAULT_IGNORE = (
    ".git",
    ".github",
    "config",
    "data",
    "docs",
    "knowledge",
    "logs",
    "scratch",
    "scripts",
    "tests",
    "tmp",
    "tooling",
)

__all__ = ["CATEGORY_MARKERS", "DEFAULT_IGNORE", "classify_dir", "find_unclassified_dirs", "main"]


def classify_dir(path: Path) -> str | None:
    """Return the matching project category for ``path``, or ``None``."""
    if not path.is_dir():
        return None

    child_names = {child.name for child in path.iterdir()}
    if _has_markers(child_names, CATEGORY_MARKERS["investigation"]):
        return "investigation"
    if _has_markers(child_names, CATEGORY_MARKERS["tool"]):
        return "tool"
    if _has_markers(child_names, CATEGORY_MARKERS["pipeline"]):
        return "pipeline"
    if _looks_like_experiment(child_names):
        return "experiment"
    return None


def find_unclassified_dirs(root: Path, ignore: tuple[str, ...]) -> list[Path]:
    """Return top-level directories under ``root`` that do not match any category."""
    if not root.is_dir():
        return []

    ignored = set(ignore)
    unclassified: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name in ignored:
            continue
        if classify_dir(child) is None:
            unclassified.append(child)
    return unclassified


def main() -> None:
    """Run the advisory taxonomy audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to audit (default: this file's repo root).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when unclassified directories are found.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    unclassified = find_unclassified_dirs(root, DEFAULT_IGNORE)
    for path in unclassified:
        print(f"{path.relative_to(root)}: run PT-3's checklist before deciding this directory's category.")
    if args.strict and unclassified:
        raise SystemExit(1)


def _has_markers(child_names: set[str], markers: tuple[str, ...]) -> bool:
    return all(marker in child_names for marker in markers)


def _looks_like_experiment(child_names: set[str]) -> bool:
    if not _has_markers(child_names, CATEGORY_MARKERS["experiment"]):
        return False
    return not child_names.intersection({"docs", "scripts", "src", "tests"})


if __name__ == "__main__":
    main()
