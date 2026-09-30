"""Tests for scripts/dev/check_project_taxonomy.py."""
from __future__ import annotations

from pathlib import Path

from scripts.dev.check_project_taxonomy import classify_dir, find_unclassified_dirs


def _mkdirs(root: Path, relative_paths: tuple[str, ...]) -> Path:
    for relative_path in relative_paths:
        (root / relative_path).mkdir(parents=True, exist_ok=True)
    return root


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_classify_dir_matches_investigation_marker(tmp_path: Path) -> None:
    project_dir = _mkdirs(tmp_path / "investigation_case", ("docs", "scripts", "tests"))

    assert classify_dir(project_dir) == "investigation"


def test_classify_dir_returns_none_for_unrecognized_layout(tmp_path: Path) -> None:
    project_dir = _mkdirs(tmp_path / "mystery_dir", ("notes",))

    assert classify_dir(project_dir) is None


def test_find_unclassified_dirs_skips_ignored_and_flags_unmarked(tmp_path: Path) -> None:
    _mkdirs(tmp_path / "classified_investigation", ("docs", "scripts", "tests"))
    _mkdirs(tmp_path / "mystery_dir", ("notes",))
    _mkdirs(tmp_path / "docs", ())
    _touch(tmp_path / "README.md")

    unclassified = find_unclassified_dirs(tmp_path, ignore=("docs",))

    assert unclassified == [tmp_path / "mystery_dir"]
