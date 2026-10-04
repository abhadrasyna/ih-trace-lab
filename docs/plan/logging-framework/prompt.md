# Logging framework rollout — prompt

> Close the gap `src/lib/logging/context.py` and `docs/plan/pipeline-migration/README.md` both already flag: FCID was designed in full (`docs/archive/flow-correlation-id-logging`) but only a minimal
> slice was ever implemented, and `setup_logging()` exists but is called at almost no real entry point. This story builds the missing bootstrap, applies it where it was found missing, and makes it
> binding for all future code via the existing review checklist — not just a one-time retrofit.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A 2026-10-04 investigation of `logs/cron_daily_reports_v2.out` (the `aws-access-cli` daily cron log) found: no entry point under `src/pipelines/aws_access_cli/` or `investigations/ctap-smvod/` calls
`setup_logging()`, so every log record falls back to Python's `logging.lastResort` (WARNING-floor, no formatter, no file) — happy-path `INFO`/`DEBUG` calls that do exist (mostly in the vendored
`athena_runner` layer) are silently dropped, and the few `ERROR`/`exception` calls that do surface have no timestamp, level, or logger-name prefix and are sometimes logged twice (once bare, once
inside a re-raised traceback). Separately, `src/lib/athena/adapter.py` (the module the pipeline actually imports) and all three `aws_access_cli` business-logic modules have zero happy-path logging of
their own, and `investigations/ctap-smvod/` (23 scripts) has none at all. Report-preview tables are `print()`ed unconditionally and land in the same cron output file as the operational log.

This traces back to a known, explicitly-flagged gap: `docs/archive/flow-correlation-id-logging`'s FCID-1/FCID-2 tasks were scoped **design-only** on purpose ("future implementation, not this story").
A later session built the minimal `contextvars` slice (`src/lib/logging/context.py`) only because `athena-lib-integration` ALI-5 structurally needed it — that module's own docstring states it
"deliberately does NOT... wire `%(fcid)s` into any project-wide `setup_logging()` formatter... those remain future work for whichever session picks up the deferred FCID implementation task **in
full**." The `pipeline-migration` epic's own `README.md` coordination note says the same thing from the other side: both its stories "rely on `src/lib/*` adapters to auto-inject [FCID]... neither
story implements the convention itself." No task ever picked it up. This story is that pickup.

## Scope guard

**In scope:** the FCID/logging bootstrap itself (`src/lib/logging/`), the minimum logging contract definition, applying both to `src/lib/athena/adapter.py` and the `aws_access_cli` pipeline (the
concrete, evidenced-missing case this story was triggered by), separating report-preview `print()` output from the operational log stream for that same pipeline, and making the contract a binding
review-checklist item for all future code project-wide.

**2026-10-04 reopen (LFR-6..8):** the LFR-5 deferral above was revisited the same day, after a follow-up investigation of `logs/pipeline.log` vs `logs/cron_daily_reports_v2.out` confirmed the format
gap was real and still undocumented-as-fixed. User explicitly approved expanding scope to retrofit every remaining consumer (`investigations/ctap-smvod/`'s 24 scripts, `scripts/athena/`,
`scripts/dev/` excluding hook/tooling scripts, `scripts/reference_diagram/main.py`, `scripts/resolve_tenant.py`) and to add automated pre-commit enforcement so future entry points can't silently skip
`init_logging()`. See `tasks.md`'s LFR-6a/6b/7/8 and `stories.md` for the full specs.

**Out of scope (flagged, not silently dropped):** `scripts/dev/hooks/*.py` and `tooling/docs-plan/*.py` (pre-commit hook entry points — `print()` to pre-commit's console is their documented output
contract, not a log line) and `scratch/*.py` (pre-production POC, not yet subject to any project-wide contract per `scratch/SCRATCH.md`). Does not change any report's business logic or output
*values*, only its logging/output plumbing. Does not add a structured/JSON log formatter (plain-text format stays; a JSON formatter is a clean future extension of the bootstrap, not required here).

## Session-start load hints

- `docs/refactor/logging-and-correlation-id.md` — the FCID convention this story implements; read before LFR-1.
- `docs/archive/flow-correlation-id-logging/stories.md` — FCID-1's original full spec (format, generation point, redaction); `src/lib/logging/bootstrap.py` must match it exactly, not reinvent it.
- `src/lib/logging/context.py` and `src/lib/logging/setup.py` — read both before LFR-1; the bootstrap composes these, it does not replace them.
- `docs/refactor/code-review-checklist.md` — read before LFR-4; the new "Logging" section follows the same one-box-per-trigger shape as its existing FCID section.
- `docs/plan/pipeline-migration/aws-access-cli-pipeline-migration/` — read before LFR-3; `run_daily_reports.py`/`run_weekly_reports.py`/`run_monthly_reports.py`/`schedule.py` live there.

## Task overview

1. **LFR-1** — Build `src/lib/logging/bootstrap.py`'s `init_logging()` (setup + FCID bind + `%(fcid)s` formatter wiring + `redact_params()`).
2. **LFR-2** — Define the minimum logging contract; apply it to `src/lib/athena/adapter.py` and the `aws_access_cli` business-logic modules.
3. **LFR-3** — Call `init_logging()` at all `aws_access_cli` entry points; separate preview-table output from the log stream.
4. **LFR-4** — Add a "Logging" section to `code-review-checklist.md`; update `CONTEXT.md`.
5. **LFR-5** — Dated coordination notes in `investigations/ctap-smvod` and other unretrofitted scripts' own docs.

## Definition of done

`src/lib/logging/bootstrap.py` exists, tested, and is the single call every entry point makes; `src/lib/athena/adapter.py` and the `aws_access_cli` business-logic layer log run start/end and every
external-call start/success/failure at the levels the contract states; every `aws_access_cli` `run_*.py` calls it and no longer mixes report-preview tables into the same stream as operational logs;
`code-review-checklist.md` and `CONTEXT.md` reflect the new binding contract; `investigations/ctap-smvod` and other non-retrofitted consumers carry a dated one-line coordination note pointing here.

## Perspectives not covered

- **Cross-process FCID propagation** (a pipeline step shelling out to a subprocess) is still the open question FCID-1 itself deferred — this story does not resolve it either; a future story
  introducing a real multi-process pipeline step should pick it up then, per FCID-1's own note.
- **A structured/JSON log formatter** is not built here; the bootstrap is designed so adding one later is a formatter swap, not a call-site rewrite, but that swap itself is future work.
- **Log rotation/retention** for `logs/app.log` (currently unbounded, per `setup.py`'s own docstring) is unrelated to this story's scope and is not addressed here.
