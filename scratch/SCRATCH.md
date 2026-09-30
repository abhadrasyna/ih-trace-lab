# SCRATCH.md — Guideline for `scratch/` scripts

`scratch/` holds quick POCs: throwaway scripts that prove or disprove an idea fast enough to inform a concrete design, before any production code gets written. They are not held to `src/`-level
discipline — no mandatory tests, no type-hint enforcement, no requirement to reuse existing production libraries. Optimize for speed of proving the point, not for elegance.

No throwaway code is ever written directly in `src/`/`scripts/` — a quick POC or exploration always starts here first, and only graduates via the convergence rule below once it's proven.

## Naming

`YYYY-MM-DD_topic_purpose.py` (or `.md` for a question/handoff doc, `.sh` for a one-off shell probe). The date is load-bearing — it's how a later session tells "this already answered that" from "this
is stale."

Stay flat (no subfolders) until this folder passes roughly 50 files — at that point, revisit whether purpose-subfolders earn their keep. Do not pre-create empty buckets before that point.

## Registry & duplicate-check (before writing a new scratch script)

Before creating any new scratch analysis/probe script, delegate a bounded sub-agent task (`task` or `general-purpose`) to read root `SCRIPTS.md` — both the "Scripts" and "Scratch (unpromoted — check
here before writing a new one)" sections — and check whether the topic/question already has coverage.

Hard requirement:

- If the sub-agent finds a matching reusable script or scratch probe, it reports the path and stops. Reuse the existing file; do not create a new near-duplicate.
- If the sub-agent finds no match, that same sub-agent creates the new stub file as `scratch/<YYYY-MM-DD>_<topic>_<purpose>.py` and then returns control to the main session.

This is delegated rather than done inline so the duplicate-check plus stub-creation boilerplate stays out of the main session's context window, and so the check becomes a named, auditable step instead
of something easy to skip under time pressure.

Commands this workflow depends on:

- `python scripts/dev/generate_scripts_registry.py` — regenerate root `SCRIPTS.md` after `scripts/` or `scratch/` changes. `session-close` also runs this when applicable.
- `python scripts/dev/promote_scratch_scripts.py --list [--days N]` — list aged scratch scripts that may be ready for promotion.
- `python scripts/dev/promote_scratch_scripts.py --script <path>` — manually promote one scratch script into `scripts/dev/` and refresh the registry in the same command.

## The convergence rule

A scratch script answers one of two kinds of question, and they graduate differently:

**"What does the data/API/plumbing look like?"** (a probe) — if you've written the *same* fetch/parse/connect boilerplate in 3 or more scratch scripts, that's proof the plumbing is stable enough to
stop re-deriving. Extract it into `scratch/_lib/` (see below) immediately — don't wait for a 4th rewrite.

**"What should this feature/logic look like?"** (a design POC) — if you've reproven the *same* design shape 2 or more times, check `src/` first before writing a 3rd. Two outcomes:
- A production module already solves it → stop writing new scratch versions, just call the existing module. No promotion needed.
- No production module solves it → the convergence itself is the signal to stop proving and start building. Promote to `scripts/dev/<name>.py` (tested CLI) or `src/<module>/<name>.py` (tests, type
  hints, full `AGENTS.md` discipline). Do not leave the converged pattern sitting in `scratch/` as a 3rd near-duplicate.

Do not extract or promote preemptively on a single occurrence — that's speculative abstraction. Wait for the actual 2nd/3rd repeat.

Separate boundary: bulk/sweep/migration logic that might re-run on other targets goes straight to `scripts/dev/` as a tested CLI — it never passes through `scratch/` first, convergence rule or not.

## `scratch/_lib/` — abstracted plumbing, not production code

Holds helpers extracted under the convergence rule above:

- Purpose is to stop re-deriving low-level plumbing inside new POCs — not to be a production dependency.
- No test file required, same relaxed bar as the rest of `scratch/`.
- Every file must open with a one-line docstring: `"""Scratch-only helper — not for src/ or scripts/dev/ import. Graduate (with tests) before reuse there."""`
- When a `_lib/` helper itself gets reused by a 3rd *production-bound* script, that's the trigger to move the helper itself into `scripts/dev/` or `src/` alongside the graduating script — with tests,
  at that point.
