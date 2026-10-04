"""Tests for scripts/dev/hooks/check_logging_contract.py."""
from __future__ import annotations

from pathlib import Path

from scripts.dev.hooks.check_logging_contract import find_entry_points_missing_init_logging

ENTRY_POINT_MISSING_INIT_LOGGING = '''\
def main() -> int:
    print("hello")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

ENTRY_POINT_WITH_INIT_LOGGING = '''\
from src.lib.logging.bootstrap import init_logging


def main() -> int:
    init_logging("demo-script")
    print("hello")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_flags_entry_point_missing_init_logging(tmp_path: Path) -> None:
    repo_root = tmp_path
    target = repo_root / "scripts" / "dev" / "demo_tool.py"
    _write(target, ENTRY_POINT_MISSING_INIT_LOGGING)

    assert find_entry_points_missing_init_logging([target], repo_root) == ["scripts/dev/demo_tool.py"]


def test_does_not_flag_entry_point_with_init_logging(tmp_path: Path) -> None:
    repo_root = tmp_path
    target = repo_root / "scripts" / "dev" / "demo_tool.py"
    _write(target, ENTRY_POINT_WITH_INIT_LOGGING)

    assert find_entry_points_missing_init_logging([target], repo_root) == []


def test_does_not_flag_excluded_paths_even_when_missing_init_logging(tmp_path: Path) -> None:
    repo_root = tmp_path
    hook_path = repo_root / "scripts" / "dev" / "hooks" / "demo_hook.py"
    tooling_path = repo_root / "tooling" / "docs-plan" / "demo_check.py"
    test_path = repo_root / "tests" / "dev" / "demo_test.py"
    scratch_path = repo_root / "scratch" / "demo_probe.py"
    for path in (hook_path, tooling_path, test_path, scratch_path):
        _write(path, ENTRY_POINT_MISSING_INIT_LOGGING)

    assert find_entry_points_missing_init_logging(
        [hook_path, tooling_path, test_path, scratch_path], repo_root
    ) == []


def test_does_not_flag_file_without_a_main_guard(tmp_path: Path) -> None:
    repo_root = tmp_path
    target = repo_root / "src" / "lib" / "helpers.py"
    _write(target, "def main() -> int:\n    return 0\n")

    assert find_entry_points_missing_init_logging([target], repo_root) == []
