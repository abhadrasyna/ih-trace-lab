#!/usr/bin/env python3
"""Force a plan/go-ahead checkpoint every N turns during a long autopilot run.

Registered by ``.github/hooks/autopilot-checkpoint.json`` on two events:

- ``sessionStart`` (``--init``): resets this session's turn counter to 0.
- ``agentStop`` (``--check``): increments the counter by one. Once it reaches
  ``CHECKPOINT_INTERVAL`` turns, resets to 0 and returns ``decision: "block"``
  so the CLI forces one more turn that restates the plan and waits for
  explicit go-ahead before continuing.

Why this exists: ``session_close_on_commit.py`` already forces a close-out
when a *commit* lands, and ``.github/hooks/session-context.json`` injects the
Step 1-3 reminder once at ``sessionStart`` — but neither fires mid-session.
The ``src-lib-migration`` epic's 2026-10-02 automation run executed 24
task segments inside *one* session (one per `ALI-*`/`RRM-*`/`HLM-*`/`AUM-*`/
`CIM-*`/`CPM-*` task), each resuming work with no re-check of plan/go-ahead —
`suggestions.md`'s `re-read-context-on-resumed-task-segments` (18 occurrences,
all from that single session) and repeated `state-plan-before-editing` /
`wait-for-explicit-go-ahead-before-editing` violations are the direct result.
A commit-triggered or session-start-triggered hook cannot catch that pattern;
only a turn-count-triggered one can.

Turn count, not commit count, is the trigger: several task segments in that
run touched multiple files (docs + code + tests) across more than one commit
before the next checkpoint was due, so counting commits would under-fire.
Counting every ``agentStop`` is the only signal available to a hook that
does not require parsing the transcript's task-completion semantics.

State is kept at ``<gitdir>/copilot-hooks/autopilot-turns-<sessionId>`` —
inside ``.git`` so it is never tracked, keyed by session id so concurrent
sessions on the same repo don't clobber each other's counter. A missing or
path-unsafe ``sessionId`` disables the hook for that call (returns ``{}``)
rather than falling back to a shared ``"unknown"`` counter that different
sessions could clobber. ``--init`` also prunes counter files older than
``STALE_STATE_MAX_AGE_SECONDS`` so this directory does not grow forever
across sessions that never reach a checkpoint.

Stdin carries the hook's JSON payload (camelCase ``sessionStart``/``agentStop``
input); stdout carries the hook's JSON output. See
https://docs.github.com/en/copilot/reference/hooks-reference.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

#: How many agent turns (``agentStop`` events) may pass before a checkpoint
#: is forced. Chosen to catch a multi-segment autopilot run without firing
#: on an ordinary single-task session (Step 3-5 of a normal task is usually
#: well under this many turns).
CHECKPOINT_INTERVAL = 5

#: How long a per-session counter file may sit unused before ``--init``
#: prunes it — long enough to outlive any real session, short enough that
#: ``.git/copilot-hooks/`` doesn't accumulate one file per session forever.
STALE_STATE_MAX_AGE_SECONDS = 24 * 60 * 60


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


def _state_dir(cwd: str) -> Path | None:
    git_dir = _git_dir(cwd)
    if git_dir is None:
        return None
    state_dir = git_dir / "copilot-hooks"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _state_file(cwd: str, session_id: str | None) -> Path | None:
    """Resolve this session's counter file, or None if unsafe/unavailable.

    A missing ``sessionId``, or one containing a path separator (``/`` or an
    OS path component like ``..``), disables the hook for this call rather
    than falling back to a shared counter name that a different (also
    session-id-less) session could clobber.
    """
    if not session_id or "/" in session_id or "\\" in session_id or session_id in (".", ".."):
        return None
    state_dir = _state_dir(cwd)
    if state_dir is None:
        return None
    return state_dir / f"autopilot-turns-{session_id}"


def _prune_stale_state_files(cwd: str, *, max_age_seconds: float = STALE_STATE_MAX_AGE_SECONDS) -> None:
    """Delete counter files older than ``max_age_seconds`` so the directory never grows forever."""
    state_dir = _state_dir(cwd)
    if state_dir is None:
        return
    cutoff = time.time() - max_age_seconds
    for candidate in state_dir.glob("autopilot-turns-*"):
        try:
            if candidate.stat().st_mtime < cutoff:
                candidate.unlink()
        except OSError:
            continue  # another process removed/replaced it concurrently — not this hook's problem


def _read_count(state_file: Path) -> int:
    if not state_file.exists():
        return 0
    try:
        return int(state_file.read_text(encoding="utf-8").strip())
    except ValueError:
        return 0


def handle_init(payload: dict) -> dict:
    """``sessionStart``: reset the turn counter and prune stale sessions' counter files."""
    cwd = payload.get("cwd", ".")
    _prune_stale_state_files(cwd)
    state_file = _state_file(cwd, payload.get("sessionId"))
    if state_file is not None:
        state_file.write_text("0", encoding="utf-8")
    return {}


def handle_check(payload: dict) -> dict:
    """``agentStop``: block once every ``CHECKPOINT_INTERVAL`` turns.

    Accepts both ``stop_hook_active`` (the spelling ``session_close_on_commit.py``
    already uses) and ``stopHookActive`` (this payload's own camelCase
    convention) — the hooks reference does not pin down which casing the CLI
    sends for this particular field, so checking both is cheap insurance
    against the guard silently never firing.
    """
    if payload.get("stop_hook_active") or payload.get("stopHookActive"):
        # Already forced once this turn-chain; never force twice in a row,
        # and don't let the forced checkpoint turn itself count towards the
        # next interval.
        return {}

    cwd = payload.get("cwd", ".")
    state_file = _state_file(cwd, payload.get("sessionId"))
    if state_file is None:
        return {}

    count = _read_count(state_file) + 1
    if count < CHECKPOINT_INTERVAL:
        state_file.write_text(str(count), encoding="utf-8")
        return {}

    state_file.write_text("0", encoding="utf-8")
    return {
        "decision": "block",
        "reason": (
            f"{CHECKPOINT_INTERVAL} agent turns have passed since the last "
            "checkpoint (or session start) with no re-check. If this is an "
            "autopilot/multi-task run, pause now: restate the current "
            "one-sentence plan for the *next* task segment only (files "
            "touched, tests, commit), and wait for explicit go-ahead before "
            "continuing — do not re-read CONTEXT.md or any other file "
            "already loaded earlier this session unless its content has "
            "changed since then. If this is an ordinary single-task session "
            "that legitimately needed this many turns, state that plainly "
            "and continue."
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("--init", "--check"):
        print("usage: autopilot_checkpoint.py --init|--check", file=sys.stderr)
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
