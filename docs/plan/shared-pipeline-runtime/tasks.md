# Shared pipeline runtime — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: SPR-1, SPR-2, SPR-3, SPR-4, SPR-5, SPR-6.**

- [ ] **SPR-1** — Audit and design review: before diagram, unit contract, timeout-strategy decision (docs only) | Owner: AI agent | Model: n/a | Review: user approval of the design | SHA: —
- [ ] **SPR-2** — `src/lib/pipeline_runtime`: `Unit`, `UnitResult`, `RunSummary`, status file, `run_units`, subprocess and in-process runners | Owner: AI agent | Model: n/a | Review: tests green +
  code-reviewer | SHA: —
- [ ] **SPR-3** — Run-level SSO pre-flight with rate-limited mid-run re-check | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: —
- [ ] **SPR-4** — Bounded deterministic unit pool with optional concurrency cap | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: —
- [ ] **SPR-5** — Artifact registry and dry-run-first prune | Owner: AI agent | Model: n/a | Review: tests green + dry-run read by human | SHA: —
- [ ] **SPR-6** — Run-summary health check over the shared status file | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: —

## Story done when

- **SPR-1** — the before diagram, unit contract and timeout decision are committed and approved; the AAH/LX task edits it lists are applied.
- **SPR-2** — both consumers' step/unit loops can be expressed as `run_units` with an injected runner; the status file schema is fixed and documented.
- **SPR-3** — one pre-flight call per run, one rate-limited re-check on an auth error, no traceback on failure.
- **SPR-4** — N units run concurrently with results in input order; one failure cancels nothing; the cap is respected.
- **SPR-5** — a registry drives a prune that does nothing without `--apply`; both consumers register their artifacts.
- **SPR-6** — a missing, failed or stale run is detected from the status file alone.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
