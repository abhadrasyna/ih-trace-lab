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
added to `ctap-smvod`'s `scripts/lib/tenant_context.py` (+ its regression test; done, default behaviour unchanged), and, only after the MEC-13 census names the gaps, extending `ctap-smvod`'s
`scripts/flatten_error_eventdata.py` (+ regression tests; existing columns and outputs must stay unchanged). Out of bounds: other changes to other investigations, `src/lib/*` changes beyond reuse
(extend there only if a shared-vs-specific test says so), any Lightstep/HAR input. Read-only against Athena; no runtime behaviour of other projects changes.

## Session-start load hints

- `docs/guides/query-catalog.md` before writing any SQL.
- `docs/guides/tenant-resolution.md` and `config/tenants.yaml` before any Athena call.
- `../usage.md` and `../../RETENTION.md` in this investigation.
- No `schema.md`: the story changes no persistent-storage schema.

## Task overview

Phases run in order; IDs ascend in run order (full list and acceptance in `tasks.md`; old-to-new mapping in `id-renumber-map.json`).

**A. Foundations**
- **MEC-0** — VSF-aware playback-outcome template and gap wrapper for this investigation (shared SQL untouched).
- **MEC-1** — statistics helpers (Wilson interval, control limits, concentration, agreement).
- **MEC-2** — define the error-code source and count grain; add the catalog query.

**B. Data fetch (everything local before analysis)**
- **MEC-3** — guest-login MCP check, run first among the guest tasks (docs only): is a guest-login household's later playback attempt observable under a matchable id? Records go or no-go.
- **MEC-4** — September `adoption-session-report` CSV for all OpCos in this investigation's `output/<OPCO>/daily/`, via the existing aws_access_cli runner.
- **MEC-5** — September `adoption-report` (household counts) CSV for all OpCos, via the same orchestrator.
- **MEC-6** — September `guest-session-report` CSV for all OpCos, via the same orchestrator; reads the `_sept26` debug table.
- **MEC-7** — September `shaka-error-session` CSV (distinct sessions per `PLAYER_ERROR` code per day) for all OpCos, with the `_sept26` debug table; separate from MEC-2.
- **MEC-8** — September `adoption-gap-analysis-session` CSV for all OpCos, with `attempts_sum_check` (depends on MEC-0; signed off after MEC-14).
- **MEC-9** — guest-login to playback attribution (24h), built only on a MEC-3 go.
- **MEC-10** — startup time, High Startup Time and EBVS abandonment per day.
- **MEC-11** — plays with no end record and the mid-month shift to timeouts.
- **MEC-12** — approximate Rebuffering Ratio (optional).
- **MEC-13** — eventdata shape census per OpCo and error code, then extend `flatten_error_eventdata.py` in `ctap-smvod` only for the gaps found.

**C. Validation and reconciliation**
- **MEC-14** — playback-outcome uniqueness check (one outcome per session).
- **MEC-15** — reconcile Shaka error sessions with `unified_sessions` `PLAYER_ERROR` end reasons per day for all OpCos (first ZA check: debug sessions are a superset, 12/36/145 vs 11/35/142).
- **MEC-16** to **MEC-18** — absent-session lookup, month-wide error-session classification, VPF-proxy check against Conviva's conditions.

**D. Analysis (local data)**
- **MEC-19** and **MEC-20** — household concentration ratios, top failure households.
- **MEC-21** — guest-login funnel rates and day-level co-movement with attempts (no Athena).
- **MEC-22** — Conviva comparison per OpCo.
- **MEC-23** to **MEC-27** — business vs technical evidence, Astro reference, device analysis, `is_wv` analysis, business/technical mapping (blocked on the MTN list).

**E. Synthesis**
- **MEC-28** — closing cross-OpCo playback-state report for September 2026 (docs only).
- **MEC-29** — finalize runbook, `usage.md`, `SCRIPTS.md`.

Settled definitions (verified on ZA 2026-09-15; full detail in `stories.md` MEC-8 and MEC-0): `PLAY` is an `event_type`, never an `endreason`. `REQUEST_VIEWING`/`PLAYER_ERROR` is VSF.
`REQUEST_VIEWING`/`DESTROY` is EBVS, using the broader shared rule (no `PLAY` row and a `DESTROY` on any row). `REQUEST_VIEWING`/`PLAYING` with no closing `PLAY` row is `playing_no_end_sessions`. The
six outcome columns are disjoint and their sum, `attempts_sum_check`, must equal `VOD-Playback-Attempt-Sessions`.

## Definition of done

Mirrors `tasks.md` "Story done when": the September CSVs listed there exist for all four OpCos (ZA, NG, ZM, GH), the error-code count source is documented, and everything is documented in `usage.md`
with tests green. More CSVs and analyses are added as tasks one at a time; each reference CSV the user pastes is mapped to the existing script that generates it.

## Perspectives not covered

Root-cause analysis of individual error codes, alerting/thresholds, and Lightstep cross-checks are deliberately left out.
