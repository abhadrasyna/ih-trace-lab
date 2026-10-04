#!/usr/bin/env python3
"""Archive a completed ``docs/plan/`` story (or epic) to ``docs/archive/``.

Implements the convention documented in ``docs/plan/README.md`` "Archiving a
completed story": ``git mv`` the folder, rewrite every ``docs/plan/<slug>``
cross-reference to ``docs/archive/<slug>`` across tracked Markdown, and reflow
any line that crosses the 200-char cap as a result of the longer path.

Epic-aware: a story folder nested one level under an epic (e.g.
``docs/plan/src-lib-migration/athena-lib-integration/``) is never archived on
its own — only the whole epic moves, and only once every one of its
sub-stories' ``tasks.md`` shows ``Open: none``.

Does not commit. Stages (``git add``) every touched path and leaves the
commit to the caller, per this project's human-commit-gate convention.

Run directly; ``print`` is the operator-facing output contract.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import logging

from src.lib.logging.bootstrap import init_logging  # wraps src.lib.logging.setup.setup_logging

DONE_MARKER = re.compile(r"^\*\*Open:\s*none\b", re.MULTILINE)
# A reference boundary: the match must not continue into a longer slug (e.g.
# archiving "foo" must not touch "docs/plan/foo-bar/..."). Treat anything
# that isn't a path/word character as the end of the slug.
_REFERENCE_BOUNDARY = r"(?![\w-])"
__all__ = [
    "ArchiveFailed",
    "StoryNotComplete",
    "archive",
    "main",
    "resolve_archivable_slug",
    "rewrite_references",
]


class StoryNotComplete(Exception):
    """Raised when the target slug (or one of its sub-stories) is still open."""


class ArchiveFailed(Exception):
    """Raised when ``archive`` fails partway through and rolls back the move."""


def _is_story_complete(tasks_md: Path) -> bool:
    """Return True if ``tasks_md`` states ``Open: none`` (story complete)."""
    return bool(DONE_MARKER.search(tasks_md.read_text(encoding="utf-8")))


def _epic_sub_stories(epic_dir: Path) -> list[Path]:
    """Return every immediate sub-story folder of an epic directory."""
    return sorted(p for p in epic_dir.iterdir() if p.is_dir() and (p / "tasks.md").exists())


def resolve_archivable_slug(root: Path, slug: str) -> Path:
    """Resolve ``slug`` (under ``root/docs/plan``) to the folder to archive.

    ``slug`` must be a single path component — a story nested under an epic
    (e.g. ``src-lib-migration/athena-lib-integration``) can never be archived
    on its own, only the whole epic once every sub-story is complete.

    Raises:
        ValueError: ``slug`` is not a single, safe path component.
        FileNotFoundError: ``docs/plan/<slug>`` does not exist.
        StoryNotComplete: the slug (or an epic sub-story) is not yet done.
    """
    if not slug or "/" in slug or "\\" in slug or slug in (".", ".."):
        raise ValueError(
            f"slug must be a single top-level docs/plan/ folder name, got {slug!r} "
            "— a story nested under an epic is archived only as part of the whole epic"
        )

    target = root / "docs" / "plan" / slug
    if not target.is_dir():
        raise FileNotFoundError(f"docs/plan/{slug} does not exist")

    tasks_md = target / "tasks.md"
    if tasks_md.exists():
        # Standalone story shape.
        if not _is_story_complete(tasks_md):
            raise StoryNotComplete(f"docs/plan/{slug}/tasks.md does not show 'Open: none'")
        return target

    # Epic shape: no tasks.md at the root, one per sub-story.
    sub_stories = _epic_sub_stories(target)
    if not sub_stories:
        raise FileNotFoundError(
            f"docs/plan/{slug} has neither its own tasks.md nor any sub-story tasks.md"
        )
    unfinished = [p.name for p in sub_stories if not _is_story_complete(p / "tasks.md")]
    if unfinished:
        raise StoryNotComplete(
            f"epic docs/plan/{slug} still has open stories: {', '.join(unfinished)}"
        )
    return target


def _tracked_markdown_files(root: Path) -> list[Path]:
    """Every ``.md`` file tracked by git under ``root``, resolved to absolute paths."""
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [root / line for line in out.splitlines() if line]


def _reference_pattern(slug: str) -> re.Pattern[str]:
    """Match ``docs/plan/<slug>`` only where ``<slug>`` ends at a real boundary.

    A plain substring match on ``f"docs/plan/{slug}"`` would also rewrite a
    longer, unrelated slug sharing the same prefix (e.g. archiving ``foo``
    must not touch ``docs/plan/foo-bar/...``, which is a different, still
    active story).
    """
    return re.compile(rf"docs/plan/{re.escape(slug)}{_REFERENCE_BOUNDARY}")


def rewrite_references(root: Path, slug: str) -> list[Path]:
    """Replace every ``docs/plan/<slug>`` with ``docs/archive/<slug>`` under ``root``.

    Returns the list of files actually modified.
    """
    pattern = _reference_pattern(slug)
    new = f"docs/archive/{slug}"
    changed: list[Path] = []
    for md_file in _tracked_markdown_files(root):
        if not md_file.exists():
            continue  # already moved out from under docs/plan/
        text = md_file.read_text(encoding="utf-8")
        new_text, count = pattern.subn(new, text)
        if count == 0:
            continue
        md_file.write_text(new_text, encoding="utf-8")
        changed.append(md_file)
    return changed


def archive(root: Path, slug: str) -> list[Path]:
    """Archive ``slug`` end-to-end: move, rewrite references, reflow, stage.

    Returns the list of paths passed to ``git add`` (moved dir + rewritten
    files), for the caller to report or inspect before committing.

    If ``git mv`` succeeds but a later step (reference rewrite, reflow, or
    staging) raises, the move is rolled back with ``git reset --hard`` so the
    working tree is left exactly as it was before this call, rather than
    half-migrated — ``archive`` is all-or-nothing from the caller's
    perspective.
    """
    target = resolve_archivable_slug(root, slug)
    dest = root / "docs" / "archive" / slug
    if dest.exists():
        raise FileExistsError(f"docs/archive/{slug} already exists")

    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(root), "mv", str(target.relative_to(root)), str(dest.relative_to(root))],
        check=True,
    )

    try:
        changed = rewrite_references(root, slug)

        # Reflow every file this run touched (the moved files' own content plus
        # every cross-referencing file whose line length may have shifted).
        reflow_targets = [dest] + changed
        subprocess.run(
            [sys.executable, str(root / "scripts" / "dev" / "reflow_md.py")]
            + [str(p) for p in reflow_targets],
            check=True,
        )

        staged = [dest] + changed
        subprocess.run(
            ["git", "-C", str(root), "add"] + [str(p.relative_to(root)) for p in staged],
            check=True,
        )
    except Exception as exc:
        subprocess.run(["git", "-C", str(root), "reset", "--hard", "HEAD"], check=False)
        subprocess.run(["git", "-C", str(root), "clean", "-fd", str(dest.relative_to(root))], check=False)
        raise ArchiveFailed(
            f"archiving docs/plan/{slug} failed partway through and was rolled back: {exc}"
        ) from exc
    return staged


def _dangling_references(root: Path, slug: str) -> list[str]:
    """Any remaining ``docs/plan/<slug>`` mentions after the move (should be empty)."""
    pattern = _reference_pattern(slug)
    hits: list[str] = []
    for md_file in _tracked_markdown_files(root):
        if md_file.exists() and pattern.search(md_file.read_text(encoding="utf-8")):
            hits.append(str(md_file.relative_to(root)))
    return hits


def _repo_root() -> Path:
    """Resolve the real repository root for CLI use (not called by tests)."""
    return Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )


def main(argv: list[str]) -> int:
    """CLI entry point: ``archive_completed_story.py <slug>``."""
    init_logging("archive-completed-story")
    logger = logging.getLogger("scripts.dev.archive_completed_story")
    try:
        logger.info("Run started")
        if len(argv) != 1:
            print("usage: archive_completed_story.py <slug-under-docs-plan>")
            return 2
        slug = argv[0]
        root = _repo_root()
        try:
            staged = archive(root, slug)
        except (ValueError, FileNotFoundError, StoryNotComplete, FileExistsError, ArchiveFailed) as exc:
            print(f"ERROR: {exc}")
            return 1

        dangling = _dangling_references(root, slug)
        print(f"Archived docs/plan/{slug} -> docs/archive/{slug}")
        print(f"Staged {len(staged)} path(s); review with 'git status' then commit.")
        if dangling:
            print(f"WARNING: {len(dangling)} file(s) still reference docs/plan/{slug}:")
            for path in dangling:
                print(f"  {path}")
            return 1
        return 0
    finally:
        logger.info("Run finished")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
