"""Warn (never block) when a staged ``.py`` entry point skips ``init_logging()``.

Enforced by the ``logging-contract-check`` pre-commit hook, added by
``docs/plan/logging-framework``'s LFR-7 task. Flags any staged file that
defines both a ``def main(`` function and an ``if __name__ == "__main__":``
guard (i.e. looks like a real entry point) but contains no ``init_logging(``
call anywhere in the file.

Deliberately non-blocking (always exits 0), same convention as
``check_unarchived_stories.py``: a file that merely *looks* like an entry
point (e.g. a library module with a demo ``__main__`` block) would otherwise
false-positive-block unrelated commits. Excluded path prefixes mirror
``docs/plan/logging-framework/stories.md``'s LFR-6b carve-out: pre-commit
hook scripts and the ``docs-plan`` tooling keep ``print()`` as their own
documented output contract, not a log line; ``tests/`` and ``scratch/`` are
not yet subject to the project-wide logging contract.

Run directly; ``print`` is the pre-commit output contract, not a log line.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MAIN_FUNC = re.compile(r"^def main\(", re.MULTILINE)
MAIN_GUARD = re.compile(r"""^if __name__ == ['"]__main__['"]:""", re.MULTILINE)
INIT_LOGGING_CALL = re.compile(r"\binit_logging\(")

EXCLUDED_PATH_PREFIXES = (
    "scripts/dev/hooks/",
    "tooling/docs-plan/",
    "tests/",
    "scratch/",
)


def _is_excluded(relative_path: str) -> bool:
    return any(relative_path.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES)


def find_entry_points_missing_init_logging(paths: list[Path], repo_root: Path) -> list[str]:
    """Return repo-relative paths of staged files that look like an entry point but skip ``init_logging()``."""
    flagged: list[str] = []
    for path in paths:
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if _is_excluded(relative):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if MAIN_FUNC.search(text) and MAIN_GUARD.search(text) and not INIT_LOGGING_CALL.search(text):
            flagged.append(relative)
    return flagged


def main(argv: list[str]) -> int:
    """Entry point. ``argv`` is the staged filenames pre-commit passes."""
    repo_root = Path(__file__).resolve().parents[3]
    paths = [Path(arg) for arg in argv]
    flagged = find_entry_points_missing_init_logging(paths, repo_root)
    if flagged:
        noun = "file" if len(flagged) == 1 else "files"
        print(f"NOTE: {len(flagged)} new/modified entry-point {noun} don't call init_logging() yet:")
        for relative in flagged:
            print(f"  {relative} — see docs/refactor/logging-and-correlation-id.md's minimum contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
