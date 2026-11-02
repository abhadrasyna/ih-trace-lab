# Shared pipeline runtime — prompt

> One reusable run engine (units, runner, run summary, SSO pre-flight, bounded pool, retention) that the aws-access-cli chain and the ctap-smvod daily wrapper both consume instead of each growing
> their own.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A code and plan review on 2026-11-02 compared `docs/plan/pipeline-migration/aws-access-cli-hardening/` (AAH) with `docs/plan/lightstep-daily-export-automation/` (LX). Both are building the same
orchestration features independently: a run summary and non-zero exit (AAH-1, LX-18/LX-19), per-unit timeout and failure isolation (AAH-3, LX-20), one SSO pre-flight (AAH-2, LX-24), bounded tenant
parallelism (AAH-10, LX-21), and retention (AAH-6, LX-27). The code already shows the split: `src/pipelines/aws_access_cli/schedule.py` has `SubReport` and `run_for_all_tenants` (in-process,
max-exit-code, no timeout), while `investigations/ctap-smvod/scripts/run_daily_pipeline.py` has `Step`, `StepResult`, `StepRunner`, `make_subprocess_runner` (process-group kill on timeout) and
`run_steps`. `run_pipeline._run_tenant` has a third loop over `(label, argv, skip)` tuples with a bare `subprocess.run`. SSO is built twice (`aws_access_cli.runtime.make_auth` and
`ctap-smvod/scripts/lib/runtime.ensure_valid_credentials`, both over `src.lib.auth.sso.SsoAuth`), and `scripts/lib/lightstep_parallel.py` already holds a `JobRunner` Protocol with serial and thread
implementations that AAH-10 and LX-21 would otherwise reinvent.

Building each feature twice means two status formats, two timeout semantics and two retention scripts, and a health check (LX-18) that can only read one of them. The decision: extract the engine once
into `src/lib/pipeline_runtime/` (the repo's shared-lib home, already imported by both sides), and make the AAH and LX tasks that overlap thin adopters of it
(`docs/refactor/code-deduplication-and-taxonomy.md`: audit, then one shared module per concern; `docs/refactor/design-principles.md`: DIP via `Protocol`, Template Method for the loop, Strategy for the
runner, plain dataclass tables for steps).

## Scope guard

**In bounds:** a new `src/lib/pipeline_runtime/` package with its tests, the one-time move of the generic parts of `run_daily_pipeline.py` into it, and doc edits to the AAH and LX plans. SPR-1 is
docs-only; SPR-2 to SPR-6 add code and change no report content.

**Out of bounds:** the AAH and LX consumer changes themselves (they stay in their own task lists: AAH-1/2/3/6/10, LX-17/18/19/21/22/24/27 — each now says "consumes SPR-n"); report content and CSV
layout; `vendor/athena-mcp-server`; `src/lib/auth/sso.py` internals (wrapped, not edited); the crontab (human-owned).

Dependency direction: `src/lib/pipeline_runtime` imports nothing from `src/pipelines/*` or `investigations/*`; consumers import it, never the reverse.

## Session-start load hints

- `docs/refactor/design-principles.md` and `docs/refactor/code-deduplication-and-taxonomy.md` — before SPR-1.
- `docs/refactor/architecture-diagrams.md` — SPR-1 commits a before/after diagram.
- `docs/refactor/logging-and-correlation-id.md` — before SPR-2 (FCID must reach worker threads and child processes).
- `investigations/ctap-smvod/scripts/run_daily_pipeline.py`, `src/pipelines/aws_access_cli/schedule.py`, `scripts/lib/lightstep_parallel.py`, `src/lib/auth/sso.py` — the four sources being unified.

## Task overview

- SPR-1 — audit and design review: before diagram, unit contract, and the in-process vs subprocess timeout decision (docs only).
- SPR-2 — `Unit`/`UnitResult`/`RunSummary`, the status file, `run_units` and the two runner strategies.
- SPR-3 — run-level SSO pre-flight with a rate-limited mid-run re-check.
- SPR-4 — bounded, deterministic parallel unit pool with an optional concurrency cap.
- SPR-5 — artifact registry and dry-run-first prune.
- SPR-6 — run-summary health check that reads the shared status file.

## Definition of done

Mirrors `tasks.md` "Story done when". Whole story: one package, three consumers (AAH schedule, LX daily wrapper, LX `run_pipeline`) with no private copy of the runner, summary writer, SSO pre-flight,
pool or prune logic; the AAH and LX plans reference SPR task ids instead of re-specifying the same code; every module has offline tests.

## Perspectives not covered

- Whether the AAH sub-reports should move to subprocess execution to get a real kill-on-timeout (in-process threads cannot be killed) is decided in SPR-1, but the cost of losing the per-tenant shared
  Athena client is not measured.
- Athena throttling limits with more than 4 concurrent workers are unknown; SPR-4 only provides the cap, consumers choose its value.
- `src/lib/dates`-style helper dedup (`_iso_date` ×2, `ddmmyyyy_to_iso`, next-day ×3) is left to AAH-8 and is not part of this story.
