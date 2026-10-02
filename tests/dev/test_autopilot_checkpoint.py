"""Tests for scripts/dev/hooks/autopilot_checkpoint.py."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from scripts.dev.hooks.autopilot_checkpoint import (
    CHECKPOINT_INTERVAL,
    STALE_STATE_MAX_AGE_SECONDS,
    _state_dir,
    handle_check,
    handle_init,
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


def test_check_does_not_block_before_interval_is_reached(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    for _ in range(CHECKPOINT_INTERVAL - 1):
        result = handle_check(payload)
        assert result == {}


def test_check_blocks_once_interval_is_reached(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    for _ in range(CHECKPOINT_INTERVAL - 1):
        assert handle_check(payload) == {}
    result = handle_check(payload)

    assert result["decision"] == "block"
    assert "go-ahead" in result["reason"]


def test_counter_resets_after_a_checkpoint_fires(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    for _ in range(CHECKPOINT_INTERVAL - 1):
        handle_check(payload)
    first_checkpoint = handle_check(payload)
    assert first_checkpoint["decision"] == "block"  # drove the counter up to, and through, the first checkpoint

    for _ in range(CHECKPOINT_INTERVAL - 1):
        assert handle_check(payload) == {}
    result = handle_check(payload)

    assert result["decision"] == "block"


def test_check_never_blocks_when_stop_hook_already_active(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    for _ in range(CHECKPOINT_INTERVAL + 5):
        result = handle_check({**payload, "stop_hook_active": True})
        assert result == {}


def test_check_never_blocks_with_camel_case_stop_hook_active(tmp_path: Path) -> None:
    """Guards against the CLI sending ``stopHookActive`` instead of ``stop_hook_active``."""
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root), "sessionId": "s1"}
    handle_init(payload)

    for _ in range(CHECKPOINT_INTERVAL + 5):
        result = handle_check({**payload, "stopHookActive": True})
        assert result == {}


def test_missing_session_id_disables_hook_without_crashing(tmp_path: Path) -> None:
    """No shared 'unknown' counter — a session-id-less payload is a no-op, not a crash."""
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root)}  # no sessionId at all

    handle_init(payload)
    for _ in range(CHECKPOINT_INTERVAL + 5):
        result = handle_check(payload)
        assert result == {}


def test_path_unsafe_session_id_disables_hook_without_crashing(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    payload = {"cwd": str(root), "sessionId": "../escape"}

    handle_init(payload)
    for _ in range(CHECKPOINT_INTERVAL + 5):
        result = handle_check(payload)
        assert result == {}


def test_init_prunes_stale_counter_files_from_other_sessions(tmp_path: Path) -> None:
    import os

    root = tmp_path
    _init_git_repo(root)
    handle_init({"cwd": str(root), "sessionId": "old-session"})

    state_dir = _state_dir(str(root))
    assert state_dir is not None
    stale_file = state_dir / "autopilot-turns-old-session"
    assert stale_file.exists()
    old_time = time.time() - STALE_STATE_MAX_AGE_SECONDS - 3600
    os.utime(stale_file, (old_time, old_time))

    handle_init({"cwd": str(root), "sessionId": "new-session"})

    assert not stale_file.exists()


def test_separate_sessions_keep_independent_counters(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    handle_init({"cwd": str(root), "sessionId": "s1"})
    handle_init({"cwd": str(root), "sessionId": "s2"})

    for _ in range(CHECKPOINT_INTERVAL - 1):
        handle_check({"cwd": str(root), "sessionId": "s1"})

    # s2 has had zero checks so far — must not be at the s1 session's count.
    result = handle_check({"cwd": str(root), "sessionId": "s2"})

    assert result == {}
