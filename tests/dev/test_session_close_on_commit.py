"""Tests for scripts/dev/hooks/session_close_on_commit.py."""
from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.dev.hooks.session_close_on_commit import handle_check, handle_init


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


def _commit(root: Path, message: str) -> None:
    (root / "file.txt").write_text(message, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-m", message],
        check=True,
        capture_output=True,
        text=True,
    )


def test_check_does_not_block_when_no_new_commit(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _commit(root, "seed")
    payload = {"cwd": str(root), "sessionId": "s1"}

    handle_init(payload)
    result = handle_check(payload)

    assert result == {}


def test_check_does_not_block_on_checkout_with_no_new_commit(tmp_path: Path) -> None:
    """HEAD moving to an unrelated (non-descendant) commit must not trigger session-close."""
    root = tmp_path
    _init_git_repo(root)
    _commit(root, "seed")
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    # Move HEAD to a commit with no ancestry relation to the baseline at all
    # (an orphan branch) — this is what checkout/reset/rebase onto an
    # unrelated ref looks like, as opposed to a real new commit on top.
    subprocess.run(
        ["git", "-C", str(root), "checkout", "--orphan", "unrelated"],
        check=True,
        capture_output=True,
        text=True,
    )
    _commit(root, "unrelated root commit")

    result = handle_check(payload)

    assert result == {}


def test_check_blocks_when_a_commit_landed_since_init(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _commit(root, "seed")
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    _commit(root, "second commit")
    result = handle_check(payload)

    assert result["decision"] == "block"
    assert "session-close" in result["reason"]


def test_check_never_re_blocks_when_stop_hook_already_active(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _commit(root, "seed")
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)
    _commit(root, "second commit")

    result = handle_check({**payload, "stop_hook_active": True})

    assert result == {}
