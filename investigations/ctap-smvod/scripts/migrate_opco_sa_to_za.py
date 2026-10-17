"""One-time migration: rename the whole-word OpCo code ``SA`` to ``ZA`` in text files.

Usage:
    python3 migrate_opco_sa_to_za.py --paths ../scripts ../tests ../docs ../../../config [--apply]

Dry-run by default (lists files and hit counts); ``--apply`` rewrites files. Only whole-word ``SA``
is replaced; ``__pycache__``, ``output``, ``data`` and ``logs`` are skipped. Lowercase ``sa`` is untouched.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERN = re.compile(r"\bSA\b")
SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".toml"}
SKIP_DIRS = {"__pycache__", "output", "data", "logs", ".git"}


def rename_code(text: str) -> tuple[str, int]:
    """Pure: replace whole-word SA with ZA; returns new text and replacement count."""
    return PATTERN.subn("ZA", text)


def iter_files(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for base in paths:
        if not base.exists():
            raise FileNotFoundError(base)
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for p in candidates:
            if p.is_file() and p.suffix in SUFFIXES and not SKIP_DIRS & set(p.parts):
                found.append(p)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paths", nargs="+", required=True, type=Path)
    ap.add_argument("--apply", action="store_true", help="rewrite files (default: dry-run)")
    args = ap.parse_args()
    total = 0
    for path in iter_files(args.paths):
        new, n = rename_code(path.read_text(encoding="utf-8"))
        if n:
            total += n
            print(f"{n:4d}  {path}")
            if args.apply:
                path.write_text(new, encoding="utf-8")
    print(f"{'applied' if args.apply else 'dry-run'}: {total} replacements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
