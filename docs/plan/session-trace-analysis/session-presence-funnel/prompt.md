# Session presence funnel (ctap-smvod) — prompt

> A daily, tenant-agnostic report that counts the sessions created in Lightstep (SM-VOD / SM-linear) and traces the same `sessionId`s into Athena `unified_sessions` and the debug-states table.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`sessionId` is the one key shared by Lightstep (SM-VOD / SM-linear), Athena (`unified_sessions`, debug states) and mDRM (`drmAuthToken.sessionId`); CTAP joins only through `lightstep.trace_id`. The
first question of any session-trace analysis is therefore: of the sessions Lightstep saw being created, how many show up downstream, and where do the rest disappear? Today that answer is only implicit
in the `outcome_missing` count of `*_setupsession_with_outcome.csv`, which mixes real gaps with duplicate rows and blank-`sessionId` rows.

Baseline measured by hand on 2026-10-26 from the local exports (ZA, 2026-10-24, VOD only, no linear that day): Lightstep `smvod` 4,449 rows / **4,443** distinct sessions; Athena `unified_sessions`
3,797 distinct; debug states 44,090 rows / 3,901 distinct. Of the 4,443: 3,763 in `unified_sessions`, 3,901 in debug states, 3,763 in both, **542 in neither**; 34 sessions are in `unified_sessions`
but not Lightstep, and 138 are in debug states but not `unified_sessions`. These numbers are the acceptance check for this story and the reference the daily report must reproduce.

This is the first stage of the epic's funnel; mDRM and error stages come later and are out of scope here.

## Scope guard

In bounds: new pure helpers in `investigations/ctap-smvod/scripts/lib/`, one new analysis script, its tests, an optional `run_pipeline.py` step, and docs. Out of bounds: changing the existing merge or
outcome scripts, mDRM stages, and live Lightstep calls from scripts. Reads existing local exports only (`data/lightstep/<TENANT>/`, `data/athena/<TENANT>/`); no new Athena query is needed in v1. Adds
a report; changes no existing output. **Generic by design:** no tenant code or id hardcoded; `--tenant` and `--date` are arguments and paths follow the existing `<TENANT>/` layout. Session type
(`abr-vod-` / `abr-linear-`) is derived from the `sessionId` prefix via `session_kind` in `scripts/lib/drm_funnel.py`, so the report splits VOD and linear automatically once the linear export exists
(see `linear-session-coverage/`); until then it simply shows VOD only.

## Session-start load hints

- `investigations/ctap-smvod/scripts/merge_session_outcome.py` (how `unified_sessions` and debug states are loaded, dedup rules) and `queries/athena/ctap-smvod-playback-outcome.sql`.
- `investigations/ctap-smvod/scripts/lib/drm_exports.py` and `drm_funnel.py` for the existing export readers, hourly-part handling and report layout (`output/<TENANT>/drm-analysis/`).
- `investigations/ctap-smvod/scripts/analyze_drm_funnel.py` as the template for a dated markdown + CSV (+ chart) report.
- `docs/guides/query-catalog.md` only if a new Athena query becomes necessary (it should not in v1).

## Task overview

- **PF-1** — Pure library: load session-id sets per source and compute the funnel stages, overlaps and per-`session_type` split.
- **PF-2** — Report script: dated markdown + CSV for one tenant and date, including the list of sessions missing downstream.
- **PF-3** — Characterize the missing sessions (device, OS, error codes, DRM activity) by joining existing files.
- **PF-4** — Daily operation: `run_pipeline.py` step plus a trend CSV so the funnel can be checked every day.
- **PF-5** — Validate on ZA 2026-10-24 against the baseline, extrapolate to another date and tenant, and update docs and `CONTEXT.md`.

## Definition of done

For any tenant and date with local exports, one command produces the dated funnel report and appends the day to a trend file, and the ZA 2026-10-24 run reproduces the baseline numbers above. See
`tasks.md` "Story done when".

## Open questions (append answers here)

- Day boundary: Athena filters on `timestamp_formatted = <date>` while the Lightstep export is bucketed by its own window; do the 34 Athena-only sessions come from that mismatch?
- Are local Athena exports complete versus a live query (stale or partial exports)? PF-5 decides whether a live reconciliation is needed.
- Why are 138 sessions in debug states but not `unified_sessions`: late arrival, or a genuinely different event population?
- Should "present in Athena" mean `unified_sessions`, debug states, or either (the report shows all three; the headline definition needs the user's call).

## Perspectives not covered

- No mDRM, CTAP or error stages yet; they are separate stories in this epic.
- Sessions that exist in Athena but never in Lightstep (the 34) are reported but not root-caused here.
