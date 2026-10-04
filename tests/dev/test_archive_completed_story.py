"""Tests for scripts/dev/archive_completed_story.py."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.dev import archive_completed_story as archive_completed_story_module
from scripts.dev.archive_completed_story import (
    ArchiveFailed,
    StoryNotComplete,
    archive,
    resolve_archivable_slug,
)


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-m", message],
        check=True,
        capture_output=True,
        text=True,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_standalone_story(root: Path, slug: str, *, open_marker: str) -> None:
    _write(root / "docs" / "plan" / slug / "tasks.md", f"{open_marker}\n")
    _write(root / "docs" / "plan" / slug / "prompt.md", f"Story {slug}.\n")
    _write(root / "scripts" / "dev" / "reflow_md.py", (
        "import sys\n\n"
        "def main(argv):\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main(sys.argv[1:]))\n"
    ))
    _write(root / "CONTEXT.md", f"See `docs/plan/{slug}/` for details.\n")


def test_archive_moves_story_and_rewrites_references(tmp_path: Path) -> None:
    root = tmp_path
    _seed_standalone_story(root, "demo-story", open_marker="**Open: none — story complete.**")
    _init_git_repo(root)
    _commit_all(root, "seed")

    staged = archive(root, "demo-story")

    assert (root / "docs" / "archive" / "demo-story" / "tasks.md").exists()
    assert not (root / "docs" / "plan" / "demo-story").exists()
    context_text = (root / "CONTEXT.md").read_text(encoding="utf-8")
    assert "docs/archive/demo-story" in context_text
    assert "docs/plan/demo-story" not in context_text
    assert any(p.name == "CONTEXT.md" for p in staged)


def test_resolve_archivable_slug_rejects_incomplete_story(tmp_path: Path) -> None:
    root = tmp_path
    _seed_standalone_story(root, "demo-story", open_marker="**Open: DS-3, DS-4.**")
    _init_git_repo(root)
    _commit_all(root, "seed")

    with pytest.raises(StoryNotComplete):
        resolve_archivable_slug(root, "demo-story")


def test_resolve_archivable_slug_rejects_nested_slug(tmp_path: Path) -> None:
    root = tmp_path
    _seed_standalone_story(root, "epic/sub-story", open_marker="**Open: none — story complete.**")
    _init_git_repo(root)
    _commit_all(root, "seed")

    with pytest.raises(ValueError):
        resolve_archivable_slug(root, "epic/sub-story")


def test_archive_does_not_touch_an_unrelated_longer_slug(tmp_path: Path) -> None:
    root = tmp_path
    _seed_standalone_story(root, "foo", open_marker="**Open: none — story complete.**")
    _seed_standalone_story(root, "foo-bar", open_marker="**Open: FB-1.**")
    _write(root / "CONTEXT.md", "See `docs/plan/foo/` and `docs/plan/foo-bar/` for details.\n")
    _init_git_repo(root)
    _commit_all(root, "seed")

    archive(root, "foo")

    assert not (root / "docs" / "plan" / "foo").exists()
    assert (root / "docs" / "plan" / "foo-bar").exists()  # untouched, still active
    context_text = (root / "CONTEXT.md").read_text(encoding="utf-8")
    assert "docs/archive/foo/" in context_text
    assert "docs/plan/foo-bar/" in context_text  # not rewritten to docs/archive/foo-bar


def test_archive_rolls_back_on_failure(tmp_path: Path) -> None:
    root = tmp_path
    _seed_standalone_story(root, "demo-story", open_marker="**Open: none — story complete.**")
    _init_git_repo(root)
    _commit_all(root, "seed")
    before_head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()

    # Make reflow_md.py fail so the move-then-rewrite sequence aborts partway through.
    (root / "scripts" / "dev" / "reflow_md.py").write_text(
        "import sys\nraise SystemExit(1)\n", encoding="utf-8"
    )

    with pytest.raises(ArchiveFailed):
        archive(root, "demo-story")

    # Rolled back: original location restored, nothing left half-migrated.
    assert (root / "docs" / "plan" / "demo-story" / "tasks.md").exists()
    assert not (root / "docs" / "archive" / "demo-story").exists()
    after_head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert before_head == after_head


def test_main_calls_init_logging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    init_logging = Mock()
    monkeypatch.setattr(archive_completed_story_module, "init_logging", init_logging)
    monkeypatch.setattr(archive_completed_story_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(archive_completed_story_module, "archive", lambda root, slug: [root / "docs" / slug / "tasks.md"])
    monkeypatch.setattr(archive_completed_story_module, "_dangling_references", lambda root, slug: [])

    result = archive_completed_story_module.main(["demo-story"])

    assert result == 0
    init_logging.assert_called_once_with("archive-completed-story")
