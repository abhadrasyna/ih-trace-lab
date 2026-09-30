"""Tests for scripts/dev/monitor_worktree_progress.py."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.dev.monitor_worktree_progress import (
    check_story,
    describe_missing_worktree,
    format_snapshot,
    parse_tasks_file,
    resolve_plan_tasks_path,
    resolve_worktree_path,
    validate_story_names,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Test User"], check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True, capture_output=True, text=True
    )


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True, capture_output=True, text=True)


def test_resolve_worktree_path_and_plan_tasks_path_follow_conventions(tmp_path: Path) -> None:
    assert resolve_worktree_path("my-story", tmp_path) == tmp_path / "wt-my-story"
    assert resolve_plan_tasks_path("my-story", tmp_path / "docs/plan") == tmp_path / "docs/plan/my-story/tasks.md"


def test_parse_tasks_file_splits_done_and_pending(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.md"
    _write(
        tasks_path,
        "- [x] **ST-1** — first task\n"
        "- [ ] **ST-2** — second task\n"
        "not a checkbox line\n"
        "- [X] **ST-3** — third task (capital X)\n",
    )

    done, pending = parse_tasks_file(tasks_path)

    assert done == ["ST-1", "ST-3"]
    assert pending == ["ST-2"]


def test_parse_tasks_file_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="tasks file not found"):
        parse_tasks_file(tmp_path / "does-not-exist.md")


def test_validate_story_names_flags_stories_without_tasks_file(tmp_path: Path) -> None:
    plan_root = tmp_path / "docs/plan"
    _write(plan_root / "real-story" / "tasks.md", "- [ ] **A-1** — a task\n")

    bad = validate_story_names(["real-story", "typo-story"], plan_root)

    assert bad == ["typo-story"]


def test_describe_missing_worktree_distinguishes_completed_from_not_started(tmp_path: Path) -> None:
    plan_root = tmp_path / "docs/plan"
    _write(plan_root / "done-story" / "tasks.md", "- [x] **A-1** — a task\n- [x] **A-2** — another\n")
    _write(plan_root / "fresh-story" / "tasks.md", "- [ ] **B-1** — a task\n")

    assert "already completed" in describe_missing_worktree("done-story", plan_root)
    assert "not started yet" in describe_missing_worktree("fresh-story", plan_root)


def test_check_story_returns_none_when_worktree_missing(tmp_path: Path) -> None:
    worktree_root = tmp_path / "worktrees"
    worktree_root.mkdir()

    assert check_story("absent-story", worktree_root, Path("docs/plan")) is None


def test_check_story_reads_head_and_tasks_from_worktree(tmp_path: Path) -> None:
    worktree_root = tmp_path
    worktree = worktree_root / "wt-real-story"
    _init_git_repo(worktree)
    _write(worktree / "docs/plan/real-story/tasks.md", "- [x] **A-1** — done\n- [ ] **A-2** — pending\n")
    _commit_all(worktree, "RS-1: seed tasks")

    snap = check_story("real-story", worktree_root, Path("docs/plan"))

    assert snap is not None
    assert snap.story == "real-story"
    assert snap.head_subject == "RS-1: seed tasks"
    assert snap.done_tasks == ["A-1"]
    assert snap.pending_tasks == ["A-2"]
    assert snap.dirty is False


def test_check_story_reports_dirty_working_tree(tmp_path: Path) -> None:
    worktree = tmp_path / "wt-dirty-story"
    _init_git_repo(worktree)
    _write(worktree / "docs/plan/dirty-story/tasks.md", "- [ ] **A-1** — pending\n")
    _commit_all(worktree, "DS-1: seed tasks")
    _write(worktree / "docs/plan/dirty-story/tasks.md", "- [x] **A-1** — now done\n")

    snap = check_story("dirty-story", tmp_path, Path("docs/plan"))

    assert snap is not None
    assert snap.dirty is True
    assert snap.done_tasks == ["A-1"]


def test_format_snapshot_flags_no_new_commits_against_previous() -> None:
    from scripts.dev.monitor_worktree_progress import Snapshot

    snap = Snapshot(
        story="s",
        timestamp="t",
        head_sha="abc123",
        head_subject="subj",
        dirty=False,
        dirty_files=[],
        done_tasks=["A-1"],
        pending_tasks=["A-2"],
    )

    same_head = format_snapshot(snap, previous=snap)
    fresh = format_snapshot(snap, previous=None)

    assert "no new commits since last check" in same_head
    assert "no new commits" not in fresh
    assert "next pending: A-2" in fresh
