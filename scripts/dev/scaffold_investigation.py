#!/usr/bin/env python3
"""Scaffold a new standalone investigation folder under ``investigations/``.

Implements the Investigation skeleton from ``docs/guides/project-taxonomy.md``:
``investigations/<case-id>/`` with ``docs/``, ``scripts/``, ``tests/`` directly
underneath (Rule A — no double wrap), plus a stub case doc pre-populated with
the mandatory **Inputs used** block (PT input-data section).

Does not create a ``data/`` folder here — raw inputs live under root
``data/<case-id>/{har,lightstep,athena}/`` per the taxonomy guide, created only
once a tool pull actually saves something.

Does not commit. Stages (``git add``) every created path and leaves the
commit to the caller, per this project's human-commit-gate convention.

Run directly; ``print`` is the operator-facing output contract.
"""
from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.lib.logging.bootstrap import init_logging

__all__ = ["InvestigationExists", "ScaffoldFailed", "scaffold", "main"]

_CASE_DOC_TEMPLATE = """\
# {title}

## Inputs used

- HAR: not used
- Lightstep: not used
- Athena: not used

## Findings

(TBD)
"""


class InvestigationExists(Exception):
    """Raised when ``investigations/<case-id>/`` already exists."""


class ScaffoldFailed(Exception):
    """Raised when ``scaffold`` fails partway through and rolls back the new folder."""


def _validate_case_id(case_id: str) -> None:
    if not case_id or "/" in case_id or "\\" in case_id or case_id in (".", ".."):
        raise ValueError(
            f"case_id must be a single safe path component, got {case_id!r}"
        )


def scaffold(root: Path, case_id: str, *, title: str | None = None) -> list[Path]:
    """Create ``investigations/<case_id>/`` with the standalone-case skeleton.

    Returns the list of created paths, in the order passed to ``git add``.

    Raises:
        ValueError: ``case_id`` is not a single, safe path component.
        InvestigationExists: ``investigations/<case_id>/`` already exists.
        ScaffoldFailed: folder creation succeeded but staging failed partway
            through; the new folder is removed so a retry does not hit
            ``InvestigationExists`` against a half-made, unstaged folder.
    """
    _validate_case_id(case_id)

    target = root / "investigations" / case_id
    if target.exists():
        raise InvestigationExists(f"investigations/{case_id} already exists")

    created: list[Path] = []
    try:
        docs_dir = target / "docs"
        scripts_dir = target / "scripts"
        tests_dir = target / "tests"
        for package_dir in (scripts_dir, tests_dir):
            package_dir.mkdir(parents=True)
            init_file = package_dir / "__init__.py"
            init_file.touch()
            created.append(init_file)

        docs_dir.mkdir(parents=True)
        case_doc = docs_dir / f"{case_id}-notes.md"
        case_doc.write_text(
            _CASE_DOC_TEMPLATE.format(title=title or case_id), encoding="utf-8"
        )
        created.append(case_doc)

        subprocess.run(
            ["git", "-C", str(root), "add"] + [str(p.relative_to(root)) for p in created],
            check=True,
        )
    except Exception as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise ScaffoldFailed(
            f"scaffolding investigations/{case_id} failed partway through and was rolled back: {exc}"
        ) from exc
    return created


def _repo_root() -> Path:
    """Resolve the repository root from this script's own location (not cwd).

    Deliberately avoids ``git rev-parse --show-toplevel`` against the current
    working directory: if the operator runs this from a different repo (e.g.
    the enclosing ``github_copilot/`` workspace this repo may be a submodule
    of), that would silently scaffold the folder into the wrong repo.
    """
    return Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    """CLI entry point: ``scaffold_investigation.py <case-id> [--title ...]``."""
    init_logging("scaffold-investigation")
    logger = logging.getLogger("scripts.dev.scaffold_investigation")
    logger.info("Run started")
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("case_id", help="Folder name under investigations/ (a single path component).")
        parser.add_argument("--title", help="Case doc title (default: the case-id).")
        args = parser.parse_args(argv)

        root = _repo_root()
        try:
            created = scaffold(root, args.case_id, title=args.title)
        except (ValueError, InvestigationExists, ScaffoldFailed) as exc:
            print(f"ERROR: {exc}")
            return 1

        print(f"Created investigations/{args.case_id}/")
        print(f"Staged {len(created)} path(s); review with 'git status' then commit.")
        return 0
    finally:
        logger.info("Run finished")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
