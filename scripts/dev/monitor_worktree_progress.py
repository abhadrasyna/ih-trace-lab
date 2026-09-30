"""Poll one or more background-automation worktrees for git/task progress.

Background Copilot CLI agents (task-tool dispatched, one per story) started in a *different* CLI session
are not visible via list_agents/read_agent from another session. The only reliable cross-session way to
check their progress is inspecting the worktree they're committing to, directly on disk. This script
automates that: `git log` / `git status --short` / a tasks.md-checkbox scan, for one or many stories at
once, following this project's `../wt-<story>` worktree and `docs/plan/<story>/tasks.md` conventions.

A story whose worktree does not exist yet is reported as "not started" rather than an error -- expected
for a dependency-gated story (e.g. reference-folder-diagrams) waiting on a prerequisite to merge first. A
story name with no matching docs/plan/<story>/tasks.md in the main checkout is rejected up front as a
likely typo, since that file is always committed to main regardless of whether the worktree exists.

Usage:
    python scripts/dev/monitor_worktree_progress.py --story tenant-registry --story functional-code-taxonomy

    # Poll every 5 minutes until interrupted:
    python scripts/dev/monitor_worktree_progress.py --story tenant-registry --story reference-knowledge-harvest \
        --watch --interval 300
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

CHECKBOX_RE = re.compile(r"^-\s*\[( |x|X)\]\s*\*\*([A-Za-z0-9_-]+)\*\*")
TASKS_FILE_NAME = "tasks.md"


@dataclass
class Snapshot:
    story: str
    timestamp: str
    head_sha: str
    head_subject: str
    dirty: bool
    dirty_files: list[str]
    done_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)


def resolve_worktree_path(story: str, worktree_root: Path) -> Path:
    """Return the conventional worktree path `<worktree_root>/wt-<story>` for `story`."""
    return worktree_root / f"wt-{story}"


def resolve_plan_tasks_path(story: str, plan_root: Path) -> Path:
    """Return the conventional tasks.md path `<plan_root>/<story>/tasks.md` for `story`."""
    return plan_root / story / TASKS_FILE_NAME


def run_git(worktree: Path, *args: str) -> str:
    """Run a git command in `worktree`, raising loudly on failure instead of swallowing errors."""
    result = subprocess.run(
        ["git", "-C", str(worktree), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {worktree} (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def get_head(worktree: Path) -> tuple[str, str]:
    """Return (short SHA, subject) of HEAD in `worktree`."""
    sha = run_git(worktree, "rev-parse", "--short", "HEAD")
    subject = run_git(worktree, "log", "-1", "--pretty=%s")
    return sha, subject


def get_dirty_files(worktree: Path) -> list[str]:
    """Return the list of paths reported by `git status --short` (empty if clean)."""
    status = run_git(worktree, "status", "--short")
    if not status:
        return []
    return [line.strip() for line in status.splitlines() if line.strip()]


def parse_tasks_file(tasks_path: Path) -> tuple[list[str], list[str]]:
    """Parse a tasks.md-style checklist for `- [ ] **TASK-ID**` / `- [x] **TASK-ID**` lines.

    Returns (done_task_ids, pending_task_ids). Raises FileNotFoundError if the path doesn't exist, so a
    mistyped path fails loudly instead of silently reporting "0 done / 0 pending" every poll.
    """
    if not tasks_path.exists():
        raise FileNotFoundError(f"tasks file not found: {tasks_path}")
    done: list[str] = []
    pending: list[str] = []
    for line in tasks_path.read_text().splitlines():
        match = CHECKBOX_RE.match(line.strip())
        if not match:
            continue
        checked, task_id = match.group(1), match.group(2)
        (done if checked.lower() == "x" else pending).append(task_id)
    return done, pending


def check_story(story: str, worktree_root: Path, plan_root: Path) -> Snapshot | None:
    """Return a Snapshot for `story`, or None if its worktree hasn't been created yet.

    Assumes the story name has already been validated against `plan_root/<story>/tasks.md` in the main
    checkout (see `validate_story_names`) -- a missing worktree here is treated as "not started", not a
    typo, since a dependency-gated story's worktree legitimately doesn't exist until it's launched.
    """
    worktree = resolve_worktree_path(story, worktree_root)
    if not worktree.exists():
        return None
    sha, subject = get_head(worktree)
    dirty_files = get_dirty_files(worktree)
    done, pending = parse_tasks_file(worktree / plan_root / story / TASKS_FILE_NAME)
    return Snapshot(
        story=story,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        head_sha=sha,
        head_subject=subject,
        dirty=bool(dirty_files),
        dirty_files=dirty_files,
        done_tasks=done,
        pending_tasks=pending,
    )


def validate_story_names(stories: list[str], plan_root: Path) -> list[str]:
    """Return story names with no `plan_root/<story>/tasks.md` in the main checkout (likely typos)."""
    return [story for story in stories if not resolve_plan_tasks_path(story, plan_root).exists()]


def describe_missing_worktree(story: str, plan_root: Path) -> str:
    """Explain why `story` has no worktree: already completed (per the main checkout) vs. not started yet.

    A worktree disappears both when a story hasn't been launched yet AND after it's merged and cleaned up
    (STEP 4's `git worktree remove`) -- checking the main checkout's own tasks.md disambiguates the two.
    """
    done, pending = parse_tasks_file(resolve_plan_tasks_path(story, plan_root))
    if done and not pending:
        return "already completed (all tasks checked off in the main checkout, worktree removed post-merge)"
    return "not started yet (worktree not created)"


def format_snapshot(snap: Snapshot, previous: Snapshot | None) -> str:
    """Render a snapshot as a short human-readable report, noting whether HEAD moved since `previous`."""
    lines = [f"[{snap.timestamp}] {snap.story}: HEAD {snap.head_sha} — {snap.head_subject}"]
    if previous is not None and previous.head_sha == snap.head_sha:
        lines.append("  (no new commits since last check)")
    lines.append(f"  tasks: {len(snap.done_tasks)} done / {len(snap.pending_tasks)} pending")
    if snap.pending_tasks:
        lines.append(f"  next pending: {snap.pending_tasks[0]}")
    if snap.dirty:
        lines.append(f"  working tree dirty ({len(snap.dirty_files)} file(s) uncommitted)")
    return "\n".join(lines)


def main() -> int:
    doc_summary = (__doc__ or "").splitlines()
    parser = argparse.ArgumentParser(description=doc_summary[0] if doc_summary else None)
    parser.add_argument(
        "--story",
        action="append",
        required=True,
        dest="stories",
        help="Story name to track; repeatable. Worktree/tasks.md paths follow this project's "
        "../wt-<story> and docs/plan/<story>/tasks.md conventions.",
    )
    parser.add_argument(
        "--worktree-root", type=Path, default=Path(".."), help="Parent directory holding wt-<story> dirs."
    )
    parser.add_argument(
        "--plan-root", type=Path, default=Path("docs/plan"), help="Root directory holding <story>/tasks.md."
    )
    parser.add_argument("--watch", action="store_true", help="Poll repeatedly instead of checking once.")
    parser.add_argument(
        "--interval", type=int, default=300, help="Seconds between polls when --watch is set (default 300)."
    )
    args = parser.parse_args()

    if args.interval < 1:
        print(f"error: --interval must be >= 1 (got {args.interval})", file=sys.stderr)
        return 1

    bad_names = validate_story_names(args.stories, args.plan_root)
    if bad_names:
        print(f"error: no {args.plan_root}/<story>/tasks.md found for: {', '.join(bad_names)}", file=sys.stderr)
        return 1

    previous: dict[str, Snapshot] = {}
    try:
        while True:
            for story in args.stories:
                snap = check_story(story, args.worktree_root, args.plan_root)
                if snap is None:
                    reason = describe_missing_worktree(story, args.plan_root)
                    print(f"[{datetime.now().isoformat(timespec='seconds')}] {story}: {reason}")
                    continue
                print(format_snapshot(snap, previous.get(story)))
                previous[story] = snap
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
