"""Warn (never block) when a ``docs/plan/`` story is complete but unarchived.

Enforced by the ``story-archive-check`` pre-commit hook. Scans every
``docs/plan/**/tasks.md`` for the ``Open: none`` completion marker this
project's story convention uses, and flags any whose folder has not yet been
moved to ``docs/archive/`` via ``scripts/dev/archive_completed_story.py``.

Deliberately non-blocking (always exits 0): archiving is a judgment call
(epic-sibling status, which cross-references to rewrite) that a commit-time
hook should surface, not force — see ``docs/plan/README.md`` "Archiving a
completed story".

Run directly; ``print`` is the pre-commit output contract, not a log line.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DONE_MARKER = re.compile(r"^\*\*Open:\s*none\b", re.MULTILINE)


def find_unarchived_complete_stories(plan_dir: Path) -> list[str]:
    """Return ``docs/plan``-relative slugs of complete-but-unarchived stories.

    A standalone story is flagged when its own ``tasks.md`` shows
    ``Open: none``. An epic is flagged only when every one of its immediate
    sub-stories' ``tasks.md`` files shows ``Open: none`` too — a partially
    complete epic stays put, per the archiving convention.
    """
    if not plan_dir.is_dir():
        return []

    flagged: list[str] = []
    for entry in sorted(plan_dir.iterdir()):
        if not entry.is_dir():
            continue
        tasks_md = entry / "tasks.md"
        if tasks_md.exists():
            if DONE_MARKER.search(tasks_md.read_text(encoding="utf-8")):
                flagged.append(entry.name)
            continue

        sub_stories = sorted(p for p in entry.iterdir() if p.is_dir() and (p / "tasks.md").exists())
        if sub_stories and all(
            DONE_MARKER.search((p / "tasks.md").read_text(encoding="utf-8")) for p in sub_stories
        ):
            flagged.append(entry.name)
    return flagged


def main(argv: list[str]) -> int:
    """Entry point. ``argv`` is ignored; pre-commit passes staged filenames we don't need."""
    repo_root = Path(__file__).resolve().parents[3]
    plan_dir = repo_root / "docs" / "plan"
    flagged = find_unarchived_complete_stories(plan_dir)
    if flagged:
        noun = "story" if len(flagged) == 1 else "stories"
        print(f"NOTE: {len(flagged)} docs/plan/ {noun} look complete but aren't archived yet:")
        for slug in flagged:
            print(f"  docs/plan/{slug} — run: python scripts/dev/archive_completed_story.py {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
