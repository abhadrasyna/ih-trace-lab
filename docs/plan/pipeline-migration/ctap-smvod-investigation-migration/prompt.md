# ctap-smvod investigation migration — prompt

> Port `ctap-smvod-session-report`'s recurring, part-manual/part-Athena campaign into `investigations/ctap-smvod/`, replacing its local executor/auth with `src/lib/*`, its SQL strings with
> `query-catalog`, its flat `inputCSV/`/`output/` naming with `project-taxonomy` PT-7's convention (splitting inputs by provenance into `data/{lightstep,athena}/`), while keeping its manual
> Lightstep-export step manual — this story relocates where files land, it does not automate what the source project's own docs already state cannot be automated.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/ctap-smvod-session-report` (~5,198 lines under `scripts/`, plus 45 files under `queries/`) is a real, recurring investigation: a 6-step `run_pipeline.py` orchestrator
where Step 1 (exporting 3 Lightstep CSVs by hand) is explicitly documented as not automatable, followed by 5 Athena-backed enrichment/merge/analysis steps. Its `scripts/lib/athena_runner.py` and
`scripts/lib/aws_sso.py` duplicate exactly what `src-lib-migration`'s `athena-lib-integration`/`auth-lib-migration` stories own; its `output/` directory (29 files as of the 2026-09-30 audit, e.g.
`setupsession_with_outcome_28072026.csv`) and `inputCSV/` (manual Lightstep exports and Athena pulls mixed together, also flat/date-suffixed) are the exact inefficiency the epic requester flagged.
This story is the actual port.

## Scope guard

**In bounds:** creating `investigations/ctap-smvod/` (skeleton, `data/{lightstep,athena}/`, `output/`, `RETENTION.md`), porting `run_pipeline.py` and every analyze/build/merge/extract business-logic
script, moving the 45 query files into `query-catalog`, and migrating both `inputCSV/` and `output/` to PT-7's convention.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/ctap-smvod-session-report` (read-only reference); automating Step 1's manual Lightstep export — out of scope by the source project's
own documented constraint, not a gap in this story; `src/lib/*` module internals; `query-catalog`'s catalog format; any change to `aws-access-cli` or its sibling story.

## Session-start load hints

- `docs/plan/project-taxonomy/structure.md` — the exact `investigations/<campaign-slug>/` skeleton (Rule B, recurring campaign) and its literal `ctap-smvod` example.
- `docs/plan/project-taxonomy/stories.md` PT-2 (Rule B skeleton) and PT-7 (path/filename convention, explicitly audited against this project) — read before CSM-2/CSM-3/CSM-4/CSM-5.
- `docs/plan/src-lib-migration/README.md` — confirms which `src/lib/*` modules exist, before CSM-2.
- `/Users/abhadra/github_copilot/ctap-smvod-session-report/scripts/run_pipeline.py` — read this specific file in full before CSM-2/CSM-3, it documents Step 1's manual-only status itself.
- `/Users/abhadra/github_copilot/ctap-smvod-session-report/{output,inputCSV}/` — the concrete flat-naming pattern being replaced; list (don't re-read every file) before CSM-3/CSM-5.

## Task overview

- **CSM-1** — Audit + per-file lib-vs-script classification table.
- **CSM-2** — `investigations/ctap-smvod/` skeleton + thin business-logic script ports using `src/lib/{athena,auth,csv_io}`.
- **CSM-3** — Manual Lightstep step: relocate to `data/lightstep/`, ISO-prefixed, Step 1 stays manual.
- **CSM-4** — Athena-pull step: relocate to `data/athena/`, using `src/lib/athena` adapter.
- **CSM-5** — Output reorg: `output/` to PT-7's snapshot/range/rollup convention.
- **CSM-6** — SQL extraction: 45 query files → `query-catalog`.
- **CSM-7** — Tests + `RETENTION.md` + `CONTEXT.md` pointer.

## Definition of done

`investigations/ctap-smvod/` exists, is fully tested, imports `src/lib/*` for every domain-mechanism concern, has no SQL string literals (all cataloged), its manually-exported Lightstep CSVs land in
`data/lightstep/` and Athena pulls in `data/athena/`, all outputs use PT-7's convention, and `RETENTION.md` states its rolling, no-close-out status. No file under `/Users/abhadra/github_copilot` was
touched.

## Perspectives not covered

This story does not evaluate whether Step 1's Lightstep export could be automated via the Lightstep API going forward — the source project's own docstring states it currently isn't, and this migration
ports the current process as-is; a feasibility study for automating it is a separate, unscoped concern.
