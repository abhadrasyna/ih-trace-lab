# Session error model (ctap-smvod) — prompt

> One shared definition of "the first error of a session" and of a session's playback outcome, reused by the presence funnel and later reports, so no script recomputes error or outcome logic.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`session-presence-funnel` (PF-8) needs one error per session, and the daily adoption reports need a per-session outcome. Both are currently computed in different places with different results: the
in-house outcome query (`queries/athena/ctap-smvod-playback-outcome.sql`) has no branch for a session whose `REQUEST_VIEWING` row ended in `PLAYER_ERROR` (VSF), and it groups by one day so a session
crossing midnight is split. This story fixes the definitions once, in pure code, before the funnel is built.

## Decisions (2026-10-26, user)

- **First-error rule:** the earliest error by datetime wins; every code seen is kept in `all_error_codes`. Source priority when times are equal or only one source exists: (1) mDRM non-2xx (mdrmfe,
  LRM, CDM), (2) first non-empty `errorcode` in `debug_states.csv` (error rows carry an EMPTY `state`), (3) none observed. A failed setup (`http.status_code` not 2xx on `sm-vod`) is **stage 0**: it
  has no usable `sessionId` when blank, so it stays in the setup-failed list and is not a first error.
- **Reuse, no new long table:** build on the flat error eventdata (`flatten_error_eventdata.py`) and the existing `mdrm_quality_failures` output; add no new persistent table.
- **Outcome definitions are in-house only** (not Conviva-aligned), resolved per session across days, not per day:
  - **VSF** — a `REQUEST_VIEWING` row with `endreason = PLAYER_ERROR`.
  - **EBVS** — no `PLAY` row and an `endreason = DESTROY` on any row (and not VSF).
  - **VPF** (Video Playback Failure) — a `PLAY` row with `endreason = PLAYER_ERROR`.
  - **VPT** (Video Playback Timeout) — a `PLAY` row with `endreason = TIMEOUT`.
  - **success** — a `PLAY` row with `endreason = DESTROY`.
  - **buffering_no_end** — a `BUFFERING` row but no `PLAY`, no `DESTROY` and no error end.
  - **startup_no_followup** — only a `REQUEST_VIEWING` row; nothing after it.
  - The last two replace the old `INCOMPLETE_NO_DESTROY` label; they carry the last event seen and the `endreason` (all 9 on ZA 2026-10-24 have `endreason = PLAYING`). Whether such a session was
    abandoned, lost or still running is unproven, so the names describe only what was observed.
- **Mutually exclusive order:** success, VSF, EBVS, VPF, VPT, buffering_no_end, startup_no_followup (first match wins). VSF and EBVS do not overlap in the data (a VSF session has no `PLAY` and no
  `DESTROY`).
- **Per-session counts are the headline;** the adoption report's counts are shown beside them with a reconciliation line, because rows keep landing for days after the day ends (see below).
- Cross-day rule: a session belongs to the date of its `REQUEST_VIEWING` row (`date(timestamp_formatted)`), and its outcome is resolved over all later days (look-ahead window), with a
  `crossed_midnight` flag.

## Evidence (ZA 2026-10-24, live Athena 2026-10-26)

3,805 attempts (distinct `parent_session_id` with `REQUEST_VIEWING`): success 1,187 (2 crossed midnight), VSF 2,088, EBVS 214, VPF 80, VPT 227, buffering_no_end 3, startup_no_followup 6. The adoption
report showed 3,803 / 1,188 / 2,086 / 215 and a residual of 314; the live residual is 316 (80 + 227 + 3 + 6). The difference is late-arriving rows, not a definition difference: rows for a day are
ingested for days afterwards (10-05 rows were still being ingested on 10-25).

## Scope guard

In bounds: pure helpers under `investigations/ctap-smvod/scripts/lib/`, one registered Athena query for the cross-day outcome, tests, docs. Out of bounds: changing the existing merge/outcome scripts
or adoption report producers (`src/pipelines/aws_access_cli/scripts/run_adoption_report.py`), live Lightstep calls from scripts. No tenant code or id hardcoded.

## Task overview

- **EM-1** — Pure first-error library over the flat eventdata, mDRM failures and debug states.
- **EM-2** — Cross-day outcome classifier plus the registered Athena query.
- **EM-3** — Cross-check against the error report and the adoption report, with the late-ingest reconciliation line.
- **EM-4** — Docs: `usage.md`, `CONTEXT.md`; unblock PF-8.

## Open questions

- Is the VSF label for a `PLAYER_ERROR`-only session (no `REQUEST_VIEWING` row; 21 on the ZA 2026-10-24 local export, in unified but not Lightstep or debug states) out of scope? Default: out of scope.
- Final names for VPF/VPT and the two no-end classes are open to veto.
