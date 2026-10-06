"""Tests for scripts/dev/scaffold_investigation.py."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.dev.scaffold_investigation import InvestigationExists, ScaffoldFailed, scaffold


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


def test_scaffold_creates_standalone_case_skeleton(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)

    created = scaffold(root, "mtn-sa-span-attribute-audit", title="MTN SA span attribute audit")

    case_dir = root / "investigations" / "mtn-sa-span-attribute-audit"
    assert (case_dir / "docs" / "mtn-sa-span-attribute-audit-notes.md").exists()
    assert (case_dir / "scripts" / "__init__.py").exists()
    assert (case_dir / "tests" / "__init__.py").exists()
    assert not (case_dir / "data").exists()
    assert not (case_dir / "investigations").exists()

    case_doc_text = (case_dir / "docs" / "mtn-sa-span-attribute-audit-notes.md").read_text(encoding="utf-8")
    assert "MTN SA span attribute audit" in case_doc_text
    assert "## Inputs used" in case_doc_text

    # Every created path is staged.
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    status_lines = status.splitlines()
    assert len(status_lines) == 3
    for line in status_lines:
        assert line.startswith("A "), f"expected staged add, got: {line}"
    assert len(created) == 3


def test_scaffold_rejects_existing_case_id(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    scaffold(root, "demo-case")

    with pytest.raises(InvestigationExists):
        scaffold(root, "demo-case")


@pytest.mark.parametrize("bad_case_id", ["", "foo/bar", "..", "."])
def test_scaffold_rejects_unsafe_case_id(tmp_path: Path, bad_case_id: str) -> None:
    root = tmp_path
    _init_git_repo(root)

    with pytest.raises(ValueError):
        scaffold(root, bad_case_id)


def test_scaffold_rolls_back_on_git_add_failure(tmp_path: Path) -> None:
    # No git repo here, so `git add` fails; scaffold must remove the
    # partially-created folder rather than leaving it behind unstaged.
    root = tmp_path

    with pytest.raises(ScaffoldFailed):
        scaffold(root, "demo-case")

    assert not (root / "investigations" / "demo-case").exists()
