"""Tests for scripts/dev/hooks/check_unarchived_stories.py."""
from __future__ import annotations

from pathlib import Path

from scripts.dev.hooks.check_unarchived_stories import find_unarchived_complete_stories


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_flags_standalone_complete_story(tmp_path: Path) -> None:
    plan_dir = tmp_path / "docs" / "plan"
    _write(plan_dir / "done-story" / "tasks.md", "**Open: none — story complete.**\n")
    _write(plan_dir / "open-story" / "tasks.md", "**Open: OS-1.**\n")

    assert find_unarchived_complete_stories(plan_dir) == ["done-story"]


def test_does_not_flag_epic_with_an_open_sub_story(tmp_path: Path) -> None:
    plan_dir = tmp_path / "docs" / "plan"
    _write(plan_dir / "epic" / "sub-a" / "tasks.md", "**Open: none — story complete.**\n")
    _write(plan_dir / "epic" / "sub-b" / "tasks.md", "**Open: SB-1.**\n")

    assert find_unarchived_complete_stories(plan_dir) == []


def test_flags_epic_once_every_sub_story_is_complete(tmp_path: Path) -> None:
    plan_dir = tmp_path / "docs" / "plan"
    _write(plan_dir / "epic" / "sub-a" / "tasks.md", "**Open: none — story complete.**\n")
    _write(plan_dir / "epic" / "sub-b" / "tasks.md", "**Open: none — story complete.**\n")

    assert find_unarchived_complete_stories(plan_dir) == ["epic"]
