# Monthly error code pipeline — prompt

> Delivers a repeatable, Athena-only monthly error-code report across every MTN OpCo (ZA, NG, ZM, GH; `config/tenants.yaml` calls ZA "SA").

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`investigations/mtn-monthly-error-code-analysis/` was scaffolded as a recurring campaign with no scripts yet. The goal is a monthly view of player error codes per OpCo and across all OpCos, sourced
only from Athena, so month-over-month trends are visible without Lightstep or HAR inputs.

Prior art exists (`aws-access-cli` Shaka error counts, `ctap-smvod` error eventdata export, `src/lib/athena/adapter.py`, `src/lib/csv_io/monthly_store.py`); this story reuses it rather than writing
new Athena plumbing.

## Data sources (September 2026 analysis)

Debug events tables per OpCo, named `<athena_tenant_id>_ccl_debug_events_sept26` (OpCo → id resolved via `config/tenants.yaml`). The unified session database (`unified_<athena_tenant_id>`) is
unchanged.

| OpCo | Athena tenant id | Debug events database |
|---|---|---|
| ZM | `a7vli5h8` | `a7vli5h8_ccl_debug_events_sept26` |
| GH | `is1aldzq` | `is1aldzq_ccl_debug_events_sept26` |
| NG | `jsxgloje` | `jsxgloje_ccl_debug_events_sept26` |
| ZA (registry: SA) | `e6auj7k7` | `e6auj7k7_ccl_debug_events_sept26` |

The user supplies the remaining analysis inputs one step at a time; the table name for other months is not assumed from the `sept26` suffix.

## Reuse precondition

Reuse before writing: import from the owning lib folders — `investigations/ctap-smvod/scripts/lib/` (`runtime`, `tenant_context`, `query_catalog`, `debug_event_parser`), `src/lib/*` and
`src/tenant_registry` — and call or compose the existing runners (`run_athena_error_eventdata.py`, `flatten_error_eventdata.py`, `summarize_error_eventdata.py`). New code here is limited to the month
orchestrator and any aggregation/diff logic not already present. Month-suffixed tables are selected with `resolve_tenant_context(code, table_suffix="sept26")` (default unchanged).

## Scope guard

In bounds: `investigations/mtn-monthly-error-code-analysis/{scripts,tests,docs,data,output}`, new catalog SQL under `queries/athena/`, `SCRIPTS.md`, `CONTEXT.md`, and the one `table_suffix` argument
added to `ctap-smvod`'s `scripts/lib/tenant_context.py` (+ its regression test; done, default behaviour unchanged). Out of bounds: other changes to other investigations, `src/lib/*` changes beyond
reuse (extend there only if a shared-vs-specific test says so), any Lightstep/HAR input. Read-only against Athena; no runtime behaviour of other projects changes.

## Session-start load hints

- `docs/guides/query-catalog.md` before writing any SQL.
- `docs/guides/tenant-resolution.md` and `config/tenants.yaml` before any Athena call.
- `../usage.md` and `../../RETENTION.md` in this investigation.
- No `schema.md`: the story changes no persistent-storage schema.

## Task overview

- **MEC-0** — September `adoption-session-report` CSV for all OpCos in this investigation's `output/<OPCO>/daily/`, via the existing aws_access_cli runner.
- **MEC-1** — September `adoption-report` (household counts) CSV for all OpCos, via the same orchestrator.
- **MEC-2** — September `adoption-gap-analysis-session` CSV for all OpCos, with `attempts_sum_check`.
- **MEC-3** — define the error-code source and count grain; add the catalog query.
- **MEC-4** — finalize runbook, `usage.md`, `SCRIPTS.md`.

## Definition of done

Mirrors `tasks.md` "Story done when": the September CSVs listed there exist for all four OpCos (ZA, NG, ZM, GH), the error-code count source is documented, and everything is documented in `usage.md`
with tests green. More CSVs and analyses are added as tasks one at a time; each reference CSV the user pastes is mapped to the existing script that generates it.

## Perspectives not covered

Root-cause analysis of individual error codes, alerting/thresholds, and Lightstep cross-checks are deliberately left out.
