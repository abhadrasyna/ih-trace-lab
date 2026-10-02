#!/usr/bin/env python3
"""Force a session-close pass whenever a commit lands during this session.

Registered by ``.github/hooks/session-close-trigger.json`` on two events:

- ``sessionStart`` (``--init``): records the repo's current ``HEAD`` as this
  session's baseline, so commits made *before* the session started are never
  mistaken for new work.
- ``agentStop`` (``--check``): compares ``HEAD`` against that baseline. If it
  moved, a commit happened during the turn that just ended — return
  ``decision: "block"`` so the CLI forces one more turn whose prompt asks the
  agent to invoke the ``session-close`` skill now, then update the baseline
  to the new ``HEAD`` so the *next* ``agentStop`` doesn't re-trigger (the
  close-out turn itself makes no commit, so this is self-limiting — no
  reliance needed on the CLI's 8-consecutive-block runaway guard).

Commit is the trigger, not "a task looks complete": this project's own
protocol (`AGENTS.md` Step 5c) already requires every completed task to end
in a commit, so "new commit" is a strict superset of "task completed" and is
the only one of the two a hook can detect without fragile diff/checkbox
sniffing.

State is kept at ``<gitdir>/copilot-hooks/last-closed-head-<sessionId>`` —
inside ``.git`` so it is never tracked, and keyed by session id so concurrent
sessions on the same repo don't clobber each other's baseline.

Stdin carries the hook's JSON payload (camelCase ``sessionStart``/``agentStop``
input); stdout carries the hook's JSON output. See
https://docs.github.com/en/copilot/reference/hooks-reference.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _git_dir(cwd: str) -> Path | None:
    """Resolve the real ``.git`` directory for ``cwd`` (handles worktrees)."""
    result = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = Path(cwd) / git_dir
    return git_dir


def _is_new_commit(cwd: str, previous: str, current: str) -> bool:
    """True only if ``current`` descends from ``previous`` (an actual new commit).

    HEAD can also move via ``checkout``, ``pull``, ``reset``, or ``rebase``
    with no new commit at all; ``--is-ancestor`` (strict: ``previous`` must
    be a *proper* ancestor, excluding the no-op ``previous == current`` case
    already handled by the caller) distinguishes real forward progress from
    those other ways HEAD can change.
    """
    result = subprocess.run(
        ["git", "-C", cwd, "merge-base", "--is-ancestor", previous, current],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _current_head(cwd: str) -> str | None:
    """Resolve the current commit SHA for ``cwd``, or None if unavailable."""
    result = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _state_file(cwd: str, session_id: str) -> Path | None:
    git_dir = _git_dir(cwd)
    if git_dir is None:
        return None
    state_dir = git_dir / "copilot-hooks"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"last-closed-head-{session_id}"


def handle_init(payload: dict) -> dict:
    """``sessionStart``: record the baseline HEAD. Always returns {} (no context to inject)."""
    cwd = payload.get("cwd", ".")
    session_id = payload.get("sessionId", "unknown")
    head = _current_head(cwd)
    state_file = _state_file(cwd, session_id)
    if head is not None and state_file is not None:
        state_file.write_text(head, encoding="utf-8")
    return {}


def handle_check(payload: dict) -> dict:
    """``agentStop``: block one more turn if HEAD moved since the last check."""
    if payload.get("stop_hook_active"):
        # Already forced once this turn-chain; never force twice in a row.
        return {}

    cwd = payload.get("cwd", ".")
    session_id = payload.get("sessionId", "unknown")
    head = _current_head(cwd)
    state_file = _state_file(cwd, session_id)
    if head is None or state_file is None:
        return {}

    previous = state_file.read_text(encoding="utf-8").strip() if state_file.exists() else None
    if previous == head:
        return {}  # no new commit since the last check

    state_file.write_text(head, encoding="utf-8")
    if previous is None:
        # First check this session with no sessionStart baseline on record
        # (e.g. hooks reloaded mid-session) — establish the baseline, don't
        # force a turn based on an unknown prior state.
        return {}

    if not _is_new_commit(cwd, previous, head):
        # HEAD moved via checkout/pull/reset/rebase, not a new commit on top
        # of the baseline — nothing to close out.
        return {}

    return {
        "decision": "block",
        "reason": (
            "A git commit landed during the turn that just ended (HEAD moved "
            f"{previous[:12]} -> {head[:12]}). Per this project's protocol, "
            "invoke the session-close skill now (as a fresh subagent against "
            "this session's transcript) before ending the turn. Do not make "
            "any further commits as part of this close-out turn — session-close "
            "only reports/audits; if it would normally commit a generated "
            "report, leave that for the next real change instead, so this "
            "turn cannot itself re-trigger this same hook."
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("--init", "--check"):
        print("usage: session_close_on_commit.py --init|--check", file=sys.stderr)
        return 2

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    handler = handle_init if argv[0] == "--init" else handle_check
    print(json.dumps(handler(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
