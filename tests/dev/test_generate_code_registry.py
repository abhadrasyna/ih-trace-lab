"""Tests for scripts/dev/generate_code_registry.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.dev import generate_code_registry as generate_code_registry_module
from scripts.dev.generate_code_registry import build_registry


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_registry_lists_near_duplicate_scripts_and_shared_modules(tmp_path: Path) -> None:
    _write(
        tmp_path / "investigations" / "applause" / "scripts" / "load_har_entries.py",
        '"""Load HAR log entries for Applause."""\n\n'
        'def load_har_entries() -> list[str]:\n'
        '    return ["applause"]\n',
    )
    _write(
        tmp_path / "experiments" / "probe" / "scripts" / "load_har_entries.py",
        '"""Load HAR log entries for a probe."""\n\n'
        'def load_har_entries() -> list[str]:\n'
        '    return ["probe"]\n',
    )
    _write(tmp_path / "src" / "lib" / "har" / "__init__.py", '"""HAR helpers."""\n')
    _write(
        tmp_path / "src" / "lib" / "har" / "protocols.py",
        '"""Protocol skeletons for HAR."""\n\nclass HarEntryLoader:\n    pass\n',
    )

    registry = build_registry(tmp_path)

    assert "| `investigations/applause/scripts/load_har_entries.py` | `load_har_entries` | Load HAR log entries for Applause. |" in registry
    assert "| `experiments/probe/scripts/load_har_entries.py` | `load_har_entries` | Load HAR log entries for a probe. |" in registry
    assert "| `src/lib/har` | `HarEntryLoader` | HAR helpers. |" in registry


def test_build_registry_handles_empty_tree_without_error(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    assert "## Scripts" in registry
    assert "## Shared modules" in registry
    assert registry.count("| — | — | — |") == 2


def test_main_calls_init_logging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    init_logging = Mock()
    out_path = tmp_path / "CODE_REGISTRY.md"
    monkeypatch.setattr(generate_code_registry_module, "init_logging", init_logging)
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_code_registry.py", "--root", str(tmp_path), "--out", str(out_path)],
    )

    generate_code_registry_module.main()

    assert out_path.exists()
    init_logging.assert_called_once_with("generate-code-registry")
