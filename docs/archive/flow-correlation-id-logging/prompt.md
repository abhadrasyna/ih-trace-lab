# Flow-correlation-id logging — prompt

> Design a project-wide flow-correlation-id (FCID) logging convention — one unique id per run/invocation, auto-propagated into every log line without threading it through call signatures — so a single
> Athena query, adapter call, and pipeline run can be traced end-to-end from logs alone.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing anything. One task per session. Complete it fully. Stop.

## Why this story exists

A 2026-10-01 design review of `src-lib-migration`, `pipeline-migration`, and `reference-code-gap-migration` found none of the three plans' adapter/logging tasks name a correlation-id mechanism.
Without one, debugging a slow/stuck Athena query or a multi-step pipeline failure means grepping disjoint log lines by timestamp and hoping they line up — exactly the kind of thing that is cheap to
design now, at the `src/lib/athena/adapter.py` seam (`athena-lib-integration` ALI-2, not yet implemented), and expensive to retrofit once a dozen consumer scripts already log without it.

This story is **design-only**: it defines the FCID convention (what it is, where it's generated, how it propagates, what it looks like in a log line) and produces reference Mermaid diagrams showing
that propagation across `src/lib/*` and the three existing plans' consumers. It does not implement a `src/lib/logging/` module or touch any adapter code — that is deliberately deferred to a follow-up
story once a real consumer needs it (matching `functional-code-taxonomy`'s own YAGNI stance for `Protocol`-bearing modules).

## Scope guard

- **In bounds:** this story's own `stories.md` (the FCID convention spec + diagrams); one coordination note appended to each of `src-lib-migration/README.md`, `pipeline-migration/README.md`,
  `reference-code-gap-migration/README.md`.
- **Out of bounds:** no `src/lib/logging/` (or similarly named) module, no `Protocol`, no code, no tests. No edit to any task already checked `[x]` in another story. No file under
  `/Users/abhadra/github_copilot` (read-only reference, unaffected either way — this story has no reason to open that tree).
- Changes **no runtime behaviour** — docs/plan only.

## Session-start load hints

- `PYTHON_DESIGN.md` — DIP/Protocol conventions this design must stay consistent with, even though no code lands here.
- `src/lib/athena/protocols.py` and `docs/plan/src-lib-migration/athena-lib-integration/stories.md` — the first real consumer seam this convention targets; the method names in both must already be
  reconciled (flagged separately, 2026-10-01 review) before ALI-2 adopts FCID logging.
- Global `AGENTS.md` logging rule: `setup_logging()` once at process start, never `logging.basicConfig` elsewhere, never bare `logging.getLogger(__name__)` in `scripts/`.

## Task overview

- **FCID-1** — Define the FCID convention: format, generation point, propagation mechanism (`contextvars`), log-line shape; write it into `stories.md`.
- **FCID-2** — Produce the reference Mermaid diagrams (sequence + component) showing FCID flowing through `src/lib/*` and each of the three plans' consumer shapes; add coordination notes to the three
  epics' `README.md`.

## Definition of done

- **FCID-1** — the convention is fully specified in `stories.md` with no open questions left for a future implementing story to invent on the spot.
- **FCID-2** — both diagrams render (checked via a Mermaid-aware viewer or `mmdc`/GitHub preview) and all three epics' `README.md` carry a dated coordination note pointing here.

## Perspectives not covered

- This design does not address **cross-process** correlation (e.g. an FCID surviving a cron-triggered subprocess boundary, or being attached to an Athena query's own `QueryExecutionId` tags) — only
  in-process propagation via `contextvars` is designed here. Cross-process/Athena-tag propagation is flagged as an open question in `stories.md` for a future session to pick up once
  `athena-lib-integration` actually lands.
