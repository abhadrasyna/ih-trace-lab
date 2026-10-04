"""Tests for scripts/dev/generate_scripts_registry.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.dev import generate_scripts_registry as generate_scripts_registry_module
from scripts.dev.generate_scripts_registry import (
    build_registry,
    extract_purpose,
    extract_scratch_date,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_extract_purpose_reads_python_docstring_first_line(tmp_path: Path) -> None:
    script = tmp_path / "example.py"
    _write(
        script,
        '"""First line.\n\nMore detail.\n"""\n\nprint("ok")\n',
    )
    assert extract_purpose(script) == "First line."


def test_extract_purpose_returns_none_when_no_docstring_or_comment(tmp_path: Path) -> None:
    py_script = tmp_path / "no_docstring.py"
    sh_script = tmp_path / "no_comment.sh"
    _write(py_script, 'print("ok")\n')
    _write(sh_script, "#!/bin/sh\nprintf 'ok\\n'\n")
    assert extract_purpose(py_script) is None
    assert extract_purpose(sh_script) is None


def test_extract_scratch_date_parses_leading_date() -> None:
    assert extract_scratch_date(Path("scratch/2020-01-01_bar_probe.py")) == "2020-01-01"


def test_extract_scratch_date_returns_none_for_non_dated_filename() -> None:
    assert extract_scratch_date(Path("scratch/helper_probe.py")) is None


def test_build_registry_lists_scripts_and_scratch_sections_separately(tmp_path: Path) -> None:
    _write(tmp_path / "scripts" / "foo.py", '"""Foo purpose."""\n')
    _write(tmp_path / "scratch" / "2020-01-01_bar_probe.py", '"""Bar purpose."""\n')

    registry = build_registry(tmp_path)

    assert "## Scripts" in registry
    assert "| `scripts/foo.py` | Foo purpose. |" in registry
    assert "## Scratch (unpromoted — check here before writing a new one)" in registry
    assert "| `scratch/2020-01-01_bar_probe.py` | 2020-01-01 | Bar purpose. |" in registry


def test_main_calls_init_logging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    init_logging = Mock()
    out_path = tmp_path / "SCRIPTS.md"
    monkeypatch.setattr(generate_scripts_registry_module, "init_logging", init_logging)
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_scripts_registry.py", "--root", str(tmp_path), "--out", str(out_path)],
    )

    generate_scripts_registry_module.main()

    assert out_path.exists()
    init_logging.assert_called_once_with("generate-scripts-registry")
