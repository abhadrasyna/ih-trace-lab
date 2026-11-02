# aws-access-cli hardening — prompt

> Make the daily/weekly/monthly aws-access-cli chain observable, failure-tolerant and de-duplicated, without changing any report's content.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A read-only review on 2026-11-02 of `src.pipelines.aws_access_cli.scripts.run_daily_reports` found a chain that works but has no run-level record or alerting. The last daily run (fcid
`aws-access-cli-daily-reports-20261102T063922-f9e3a99f`) ran 163 Athena queries serially in 593s across 4 tenants × 6 sub-reports × 8 dates. Failures are swallowed into a max exit code that cron never
reads (`schedule.py:31-44`, crontab line 125); a preflight failure aborts the run uncaught (`schedule.py:28`); SSO is checked once although a run takes about 10 minutes; `--force` applies only to the
last date (`run_daily_reports.py:45`); and 34 header-only position CSVs (NG 30, GH 4) count as "not produced" and are re-queried on every run (`existing_output.py:18`).

Maintainability debt sits in `scripts/common.py` (490 lines): three near-identical `run_*_cli` runners, `args` passed whole into helpers, string-typed artifact identity, and helpers duplicated across
modules (`_iso_date` ×2, next-day ×3, `_batched` ×2, error codes 1001–1010 ×3). Outputs total 14 MB, 93% of it position-report CSVs no code reads, with no retention; `app.log` is 23.7 MB and
unrotated.

## Scope guard

**In bounds:** `src/pipelines/aws_access_cli/` (schedule, scripts, business modules, tests), the pipeline's own retention script under `scripts/`, and this story's docs.

**Out of bounds:** report content and column layout (every refactor task must leave existing CSVs byte-identical for the same inputs, unless the task says otherwise); `src/lib/*` internals;
`vendor/athena-mcp-server`; the crontab itself and AAM-5 (human-owned, unchanged); `investigations/ctap-smvod` readers.

Runtime behaviour changes in AAH-1 to AAH-6 and AAH-9/10; AAH-7/8 are behaviour-preserving refactors.

## Session-start load hints

- `docs/refactor/design-principles.md` (SOLID triggers, Python-native patterns) and `docs/refactor/code-deduplication-and-taxonomy.md` — before AAH-7 or AAH-8.
- `docs/refactor/logging-and-correlation-id.md` — before AAH-1 or AAH-2.
- `docs/plan/pipeline-migration/aws-access-cli-pipeline-migration/stories.md` — original port specs; AAM-5 stays open there.
- `queries/athena/aws-access-cli_*.sql` — before AAH-9.

## Task overview

- AAH-1 — run summary record and non-zero-exit alerting.
- AAH-2 — preflight failure isolation and mid-run SSO re-check.
- AAH-3 — per-unit timeout and per-metric isolation.
- AAH-4 — empty-day sentinel so header-only CSVs stop being re-queried.
- AAH-5 — `--force` scope fix and documentation.
- AAH-6 — retention for `output/`, `app.log` and cron `.out` files.
- AAH-7 — `ReportSpec` registry and a single `run_report`.
- AAH-8 — deduplicate date, batch and error-code helpers.
- AAH-9 — merge shaka queries and combine `unified_sessions` metrics.
- AAH-10 — parallelise tenants.

## Definition of done

Mirrors `tasks.md` "Story done when". Whole story: a failed unit is visible in a status file and a non-zero exit; no unit can hang a run; no duplicated helpers remain; query count per daily run is
lower than the 163 measured baseline with identical CSV content; every change has offline tests.

## Perspectives not covered

Athena bytes scanned and cost per query were not measured (no source for them in the logs); the saving from AAH-9 is therefore an estimate until measured. Weekly, monthly and backfill wrappers benefit
from AAH-7 but their own retry and window behaviour is not reviewed here. Position-report CSVs have no known reader; whether to stop producing them is a product decision left out of this story.
