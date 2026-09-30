"""Tests for scripts/dev/promote_scratch_scripts.py."""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.dev.promote_scratch_scripts import find_promotion_candidates, promote


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test User"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True, capture_output=True, text=True)


def _dated_name(days_ago: int, slug: str) -> str:
    stamp = (datetime.now(timezone.utc).date() - timedelta(days=days_ago)).isoformat()
    return f"{stamp}_{slug}.py"


def test_find_promotion_candidates_filters_by_age(tmp_path: Path) -> None:
    scratch_dir = tmp_path / "scratch"
    old_script = scratch_dir / _dated_name(90, "old_probe")
    new_script = scratch_dir / _dated_name(2, "new_probe")
    _write(old_script, '"""Old purpose."""\n')
    _write(new_script, '"""New purpose."""\n')

    candidates = find_promotion_candidates(scratch_dir, min_age_days=30)

    assert candidates == [old_script]


def test_find_promotion_candidates_returns_empty_when_none_eligible(tmp_path: Path) -> None:
    scratch_dir = tmp_path / "scratch"
    _write(scratch_dir / _dated_name(1, "fresh_probe"), '"""Fresh purpose."""\n')

    assert find_promotion_candidates(scratch_dir, min_age_days=30) == []


def test_promote_moves_file_and_regenerates_registry(tmp_path: Path) -> None:
    root = tmp_path
    scratch_script = root / "scratch" / _dated_name(90, "stable_probe")
    dest_dir = root / "scripts" / "dev"
    _write(scratch_script, '"""Stable purpose."""\n')
    _write(dest_dir / "existing.py", '"""Existing purpose."""\n')
    _init_git_repo(root)
    subprocess.run(["git", "-C", str(root), "add", "scratch", "scripts"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-m", "seed"],
        check=True,
        capture_output=True,
        text=True,
    )

    destination = promote(scratch_script, dest_dir)

    assert destination == dest_dir / scratch_script.name
    assert not scratch_script.exists()
    assert destination.exists()
    registry = (root / "SCRIPTS.md").read_text(encoding="utf-8")
    assert f"| `scripts/dev/{scratch_script.name}` | Stable purpose. |" in registry
    assert f"| `scratch/{scratch_script.name}` |" not in registry


def test_promote_rejects_path_outside_scratch(tmp_path: Path) -> None:
    root = tmp_path
    outside_script = root / "scripts" / "dev" / "already.py"
    dest_dir = root / "scripts" / "dev"
    _write(outside_script, '"""Existing purpose."""\n')

    with pytest.raises(ValueError, match="not under"):
        promote(outside_script, dest_dir)
