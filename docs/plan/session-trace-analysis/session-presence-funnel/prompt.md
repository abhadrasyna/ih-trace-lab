# Session presence funnel (ctap-smvod) — prompt

> A daily, tenant-agnostic report that counts the sessions created in Lightstep (SM-VOD / SM-linear) and traces the same `sessionId`s into Athena `unified_sessions` and the debug-states table.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`sessionId` is the one key shared by Lightstep (SM-VOD / SM-linear), Athena (`unified_sessions`, debug states) and mDRM (`drmAuthToken.sessionId`); CTAP joins only through `lightstep.trace_id`. The
first question of any session-trace analysis is therefore: of the sessions Lightstep saw being created, how many show up downstream, and where do the rest disappear? Today that answer is only implicit
in the `outcome_missing` count of `*_setupsession_with_outcome.csv`, which mixes real gaps with duplicate rows and blank-`sessionId` rows.

**Stage 0 — failed before a session exists (added 2026-10-26).** The Lightstep export is a superset of attempts: 4,449 rows are 4,443 distinct sessions plus **6 rows with a blank `sessionId`**. A live
Lightstep check showed all six are SetupSession spans that failed before a session was created (5 × HTTP 403, 1 × HTTP 500). The funnel therefore starts one step earlier than `sessionId`: setup
attempts → sessions created → Athena. Identifying these needs the `http.status_code` column and `setup_failed` flag from `linear-session-coverage` (LC-1/LC-2); until that re-export they can only be
counted as "blank `sessionId`", not classified.

Baseline measured by hand on 2026-10-26 from the local exports (ZA, 2026-10-24, VOD only, no linear that day): Lightstep `smvod` 4,449 rows / **4,443** distinct sessions; Athena `unified_sessions`
3,797 distinct; debug states 44,090 rows / 3,901 distinct. Of the 4,443: 3,763 in `unified_sessions`, 3,901 in debug states, 3,763 in both, **542 in neither**; 34 sessions are in `unified_sessions`
but not Lightstep, and 138 are in debug states but not `unified_sessions`. These numbers are the acceptance check for this story and the reference the daily report must reproduce.

**Late ingestion and the live re-check (added 2026-10-26).** Athena rows for a day keep arriving for days (rows for 10-05 were still ingested on 10-25), so every count is a snapshot. A live re-check
on 2026-10-26, without a date filter on the Athena side, gave for ZA 2026-10-24: `present_in_both` 3,777, `debug_not_unified` 137, `not_observed_in_athena` 529 (the local export said 3,763 / 138 /
542; 13 sessions arrived late), `unified_not_debug` 0. The baseline above is the local-export snapshot; PF-5 accepts the live figures within the late-ingest drift and records the export time.

**Attempts stage.** The funnel's "attempts" stage in the adoption report is `VOD-Playback-Attempt-Sessions` (distinct `parent_session_id` with a `REQUEST_VIEWING` row dated by
`date(timestamp_formatted)`; producer `src/pipelines/aws_access_cli/scripts/run_adoption_report.py`, session variant). The report showed 3,803 against 3,797 distinct sessions in the local unified
export; the live value is 3,805 and the live count of all sessions is 3,811, so the gap is late ingestion into a stale export, not a definition difference. The per-session outcome split of those
attempts is owned by `session-error-model/`.

**The 34 sessions in Athena but not in the Lightstep export.** All 34 are in live debug states (the local `debug_states.csv` is Lightstep-scoped, which hid them). 30 of the 34 were created in the last
1-2 minutes before 06:00, 09:00, 14:00, 18:00 or 24:00 UTC (the export part boundaries), 3 were created on 10-23 and a live Lightstep check of one sampled session found its setup span in the
05:59-06:00 bucket, so the export missed it. The live count of `sm-vod` setup spans for the day is 4,487 against 4,449 exported (0.8% short). A seam gap in the export is the likely cause but is not
proven; PF-2 flags every such session.

**Terminology and validity (added 2026-10-26).** "Missing", "dropped" and "gap" in this story's file names and task titles mean only **not observed in the Athena export**; they make no claim about
cause. It is unproven that every `sm-vod` session should appear in Athena: a setup call precedes any player telemetry, so prefetch/probe calls or an app closed early may legitimately never emit debug
events. The first question for the 542 is therefore *which sessions are expected downstream*, and only then why some are absent. A DRM license (mdrmfe HTTP 201) shows a license was issued, not that
playback happened. Every comparison of a not-observed set needs a control (the observed set) measured the same way, and DRM-based rates must be split by DRM versus no-DRM content because only DRM
content reaches mdrmfe.

The funnel covers Lightstep, mDRM (mdrmfe, LRM, CDM), debug states and `unified_sessions` (PF-7b, PF-8); the first error and the outcome come from `session-error-model/`, and further error stages are
out of scope.

## Scope guard

In bounds: new pure helpers in `investigations/ctap-smvod/scripts/lib/`, one new analysis script, its tests, an optional `run_pipeline.py` step, and docs. Out of bounds: changing the existing merge or
outcome scripts and live Lightstep calls from scripts. Reads existing local exports only (`data/lightstep/<TENANT>/` including the mDRM parts, `data/athena/<TENANT>/`) through the existing readers in
`scripts/lib/drm_exports.py`; no new Athena query is needed for PF-1 to PF-5, PF-7 and PF-8. Exception: PF-6 adds one registered Athena query for the contentId category (the local debug states file
has no `contentId`). Adds a report; changes no existing output. **Generic by design:** no tenant code or id hardcoded; `--tenant` and `--date` are arguments and paths follow the existing `<TENANT>/`
layout. Session type (`abr-vod-` / `abr-linear-`) is derived from the `sessionId` prefix via `session_kind` in `scripts/lib/drm_funnel.py`, so the report splits VOD and linear automatically once the
linear export exists (see `linear-session-coverage/`); until then it simply shows VOD only.

## Session-start load hints

- `investigations/ctap-smvod/scripts/merge_session_outcome.py` (how `unified_sessions` and debug states are loaded, dedup rules) and `queries/athena/ctap-smvod-playback-outcome.sql`.
- `investigations/ctap-smvod/scripts/lib/drm_exports.py` and `drm_funnel.py` for the existing export readers, hourly-part handling and report layout (`output/<TENANT>/drm-analysis/`).
- `investigations/ctap-smvod/scripts/analyze_drm_funnel.py` as the template for a dated markdown + CSV (+ chart) report.
- `docs/guides/query-catalog.md` only if a new Athena query becomes necessary (it should not in v1).

## Task overview

- **PF-7a** — Premise check (docs only): which sessions are expected in Athena, before any cause is discussed. Runs first.
- **PF-1** — Pure library: load session-id sets for the three sources and compute the funnel stages (starting with the setup-attempt/failed-setup stage), buckets, overlaps and per-`session_type`
  split; reuses `compare_lightstep_athena_sessions.py` and `build_session_comparison_daily.py`.
- **PF-2** — Report script: dated markdown + CSV for one tenant and date, including the setup-failure list (blank `sessionId`, by status code), the not-observed list and the `athena_only` list.
- **PF-6** — Daily debug-not-unified report: per day, the sessions present in debug states but absent from `unified_sessions`, split by whether `contentmetadata.contentid` is missing or present, with
  the sessionId list.
- **PF-7b** — Lightstep forensics of the sessions in Lightstep but not observed in Athena (529 live, 542 local export, ZA 2026-10-24): a catalogued Lightstep query, a manual per-session lifecycle
  review, and a household-concentration table.
- **PF-3** — Characterize the not-observed sessions (device, OS, hour, DRM activity; first error once PF-8 exists) by joining existing files.
- **PF-8** — Per-session trace matrix (Lightstep, mDRM, debug, unified, first error and outcome from `session-error-model`), pattern-count CSV and funnel charts; builds on PF-1 loaders and PF-7b.
- **PF-4** — Daily operation: `run_pipeline.py` step plus a trend CSV so the funnel can be checked every day.
- **PF-5** — Validate on ZA 2026-10-24 against the baseline, extrapolate to another date and tenant, and update docs and `CONTEXT.md`. Run it last, after PF-8, so it validates the whole report.

## Definition of done

For any tenant and date with local exports, one command produces the dated funnel report and appends the day to a trend file, and the ZA 2026-10-24 run reproduces the baseline numbers above. See
`tasks.md` "Story done when".

## Open questions (append answers here)

- Day boundary: **answered 2026-10-26.** 30 of the 34 Athena-only sessions sit in the last 1-2 minutes before an export part boundary (06:00, 09:00, 14:00, 18:00, 24:00 UTC) and 3 were created on
  10-23; one sampled session exists in Lightstep, so the export missed it. Seam gap likely, not proven.
- Are local Athena exports complete versus a live query? **Answered 2026-10-26: no, they lag.** Rows keep arriving for days; 13 of the 542 and 14 of the 3,811 sessions arrived after the export. Every
  report therefore records the export time and baselines carry a tolerance.
- 10-21 step change (attempts 1,327 on 10-20 to 4,039 on 10-21; households 357 to 866, only 105 of the 866 seen on any earlier day since 10-10; about 4.4 sessions per household throughout): a new
  population, not heavy users or late data. Cause unproven; 10-24 is typical only of the regime from 10-21.
- Why are 138 sessions in debug states but not `unified_sessions`: late arrival, or a genuinely different event population? Findings 2026-10-26 (ZA 2026-10-24): not a day-end effect (CREATE times span
  the whole day); 105 have only a CREATE event, 29 also have BUFFERING; a live Athena check found **137 of the 138 have a CREATE with `contentMetadata.contentId` and 1 does not**, so a missing
  contentId explains at most 1. The Clarissa Spark rule for creating a unified session is not yet confirmed (hypothesis: an event after CREATE is needed); PF-6 tracks the split every day.
- Why are 542 Lightstep sessions in neither Athena table? Findings 2026-10-26 (ZA 2026-10-24): a live Athena week query (10-21..28) found only a handful of them, all dated 10-24, so the local exports
  were slightly incomplete but the set is essentially absent. A 5-session Lightstep sample showed setup HTTP 200 in about 30-40 ms, 2 with a DELETE 204 at least 72 s later and 3 with no DELETE in the
  following 1.5 hours; none was destroyed within 3 s. PF-7 extends this to the whole set and checks household concentration. Further findings 2026-10-26: 354 of the 542 (65.3%) have an mdrmfe license
  (all HTTP 201) and 351 of those also LRM and CDM records, against 46.3% for the 3,763 observed sessions (not like-for-like: DRM content only); 188 have no trace in any source. The 542 are on 266
  devices; 215 sessions are on devices that also had an observed session that day and 159 devices have every session unobserved, so the cause is mixed and not purely a broken device population. The
  top device has 51 sessions (9%) and the top five households 21%. Cause (telemetry never sent versus ingestion gap) is unproven.
- Should "present in Athena" mean `unified_sessions`, debug states, or either? **Decided 2026-10-26 (user): present = in both `unified_sessions` AND debug states; a session in only one of them is not
  counted as present.** The report still shows all three counts, but the headline present figure is the "both" count (ZA 2026-10-24: 3,763 of 4,443; the other 680 = 138 in debug only + 542 in
  neither). The "observed" wording elsewhere in this story means present in both.

## Perspectives not covered

- No CTAP stage and no error analysis beyond PF-8's first-error rule; those are separate stories in this epic.
- Sessions that exist in Athena but never in Lightstep (the 34) are reported but not root-caused here.
