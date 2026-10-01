# Pre-implementation design review — prompt

> Review all 18 not-yet-started stories across `src-lib-migration` (6), `pipeline-migration` (2), and `reference-code-gap-migration` (10) for SOLID/clean-code and extensibility gaps *before* any of
> them starts producing code — design review is cheaper than code review.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing anything. One task per session. Complete it fully. Stop.

## Why this story exists

A 2026-10-01 design-review session found one concrete, blocking defect (a method-name mismatch between `src/lib/athena/protocols.py` and `athena-lib-integration/stories.md`'s own class diagram — would
fail that story's own ALI-2 task gate the moment someone picks it up) plus several smaller SOLID/extensibility inconsistencies across the 6 `src-lib-migration` and 2 `pipeline-migration` stories. None
of the 10 `reference-code-gap-migration` sub-stories have concrete design yet (each currently defines only an audit-only first task), so they get a lighter process-parity check instead of a line-level
critique.

This story is the formal, repeatable version of that session: `spec.md` is the audit evidence (per-story findings table, mirroring `reference-code-gap-migration`'s own `spec.md` convention),
`stories.md` holds the per-task work, and low-risk/obvious fixes are applied directly to the affected stories' own files rather than only reported — judgment-call findings are left as open questions
for a human to decide.

## Scope guard

- **In bounds:** `spec.md` (full findings), direct edits to story files for findings marked **autofix** in `spec.md`'s disposition column, one coordination-note line added to
  `reference-code-gap-migration/README.md` for the one cross-cutting process finding that applies to all 10 of its sub-stories.
- **Out of bounds:** no judgment-call finding is applied as a silent edit — each stays open, listed in `spec.md`'s "Flagged for human decision" section, until a human picks one. No code. No file under
  `/Users/abhadra/github_copilot`.
- Changes **no runtime behaviour** — docs/plan only, same as `flow-correlation-id-logging`.

## Session-start load hints

- `PYTHON_DESIGN.md` — the SOLID-as-triggers checklist this review applies verbatim.
- `docs/plan/src-lib-migration/`, `docs/plan/pipeline-migration/`, `docs/plan/reference-code-gap-migration/` — the 18 stories under review; read each target story's own `stories.md`/`tasks.md` before
  editing it, never patch from memory.
- `docs/plan/flow-correlation-id-logging/` — the prior design-review session's own output (a worked example of "design review cheaper than code," same reviewer, one day earlier).

## Task overview

- **PIR-1** — Deep SOLID/extensibility review of the 6 `src-lib-migration` stories + 2 `pipeline-migration` stories; write `spec.md`; apply the autofix-disposition findings directly to the affected
  stories' files.
- **PIR-2** — Lighter process-parity check of the 10 `reference-code-gap-migration` sub-stories (no concrete design exists yet to critique line-by-line); append findings to `spec.md`; apply the one
  cross-cutting autofix (design-time-diagram discipline parity).
- **PIR-3** — Consolidate: confirm `spec.md`'s "Flagged for human decision" section is complete and actionable on its own (no missing context), update `CONTEXT.md`.

## Definition of done

- **PIR-1** — `spec.md` has one row per src-lib-migration/pipeline-migration story with a SOLID-principle citation, severity, and disposition (autofix/flagged); every autofix row has a corresponding
  committed edit to the target story's own file.
- **PIR-2** — `spec.md` has one row per gap-migration sub-story (or one combined process-level row, since all 10 share the same gap) with the same disposition logic.
- **PIR-3** — `spec.md`'s flagged section is self-contained (a human can act on it without re-reading this story's session transcript); `CONTEXT.md` has one new "What Exists" line.

## Perspectives not covered

- This review does not re-audit `project-taxonomy`, `functional-code-taxonomy`, `query-catalog`, `tenant-registry`, `scratch-script-registry`, or `reference-knowledge-harvest` — all five are already
  marked story-complete in `CONTEXT.md`; re-reviewing landed, closed stories is a different (and more expensive, code-level) activity than this pre-implementation pass.
- Athena call-optimization/batching/caching design (flagged in the same 2026-10-01 conversation, before this story existed) is **not** re-litigated here — it is a design gap in
  `athena-lib-integration` specifically, not a SOLID/extensibility defect in the existing docs, and belongs in a future follow-up to that story, not this review.
