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

## Evidence — first error code by outcome (ZA 2026-10-24, live Athena 2026-10-26)

Attempts were 3,808 at this later check (VSF 2,091). All 3,808 have debug states; the debug side holds 3,948 sessions (137 debug-only, 3 unified without `REQUEST_VIEWING`). The first code is the first
non-empty debug `errorcode` by `datetime`; mDRM sources were not included, so this is the debug half of the rule only.

| Outcome | Sessions | First codes |
|---|---|---|
| VSF | 2,091 | 6001 1,891 (90.4%); 3016 105; 1003 27; 6002 20; 6006 9; 3015 7; 1002 7; E31012 6; 6007 6; 1001 5; 3014 3; 1006 3; 6008 2; none 0 |
| VPF | 80 | E31012 38; 1003 36; 1001 3; 1006 2; 3014 1; none 0 |
| VPT | 227 | none 217; E31012 5; 1003 5 |
| EBVS | 214 | none 207; E31012 3; 1003 1; 6002 1; 1002 1; 6001 1 |
| buffering_no_end | 3 | none 1; 1003 1; 1001 1 |
| startup_no_followup | 6 | none 5; 1003 1 |
| success | 1,187 | none 1,183; E31012 3; 1003 1 |

Observations (not causes): VSF is dominated by one code; VPF always carries a code; VPT, EBVS and the no-end classes almost never carry one, so for them the `endreason` is the only signal; a few
successful sessions still log an error code. The 217 VPT and 207 EBVS "none" sessions were checked against the mDRM exports (next section).

## Evidence — mDRM correlation (ZA 2026-10-24, mDRM parts exported 2026-10-26 morning, Athena read 2026-10-26 afternoon)

Data facts: the mDRM exports (mdrmfe, LRM, CDM) are aggregated timeseries with **no timestamp column**; request time can only be read from the `fcId` hex prefix (unix seconds; validated against the
debug `CREATE` time on 1,793 sessions: median +2.3 s, p5 0.004 s, p95 13 s). LRM and CDM carry no `sessionId`; they join through the mdrmfe `fcid`. All 14 non-2xx rows joined (0 unjoined).

| Outcome | Sessions | With an mdrmfe row | With mDRM non-2xx | Status by source |
|---|---|---|---|---|
| success | 1,187 | 1,166 | 0 | none |
| VSF | 2,091 | 133 | 5 | mdrmfe 403 ×5, LRM 400 ×4, CDM 400 ×5 |
| EBVS | 214 | 140 | 0 | none |
| VPF | 80 | 79 | 0 | none |
| VPT | 227 | 226 | 0 | none |
| buffering_no_end | 3 | 2 | 0 | none |
| startup_no_followup | 6 | 1 | 0 | none |

- All 14 non-2xx rows belong to 5 VSF sessions, all debug first code 6007, in one burst 08:50–08:58 UTC. No error exists in mDRM that is absent from debug; no success session has an mDRM failure.
- In all 5, the mDRM failure is 1–2 s earlier than the debug error, so the rule makes mDRM first for 5 of 3,808 sessions (0.13%). The two sources use different code spaces (debug 6007 against HTTP
  403/400), so merging them into one `first_error_code` would move these 5 sessions from 6007 to 403.
- 6001 (1,891 sessions) has zero mdrmfe rows: those sessions never reach mDRM. 2,086 of 2,091 VSF sessions have no mDRM failure; 1,958 have no mdrmfe row at all.
- VPT, EBVS, VPF and the two no-end classes have no mDRM failure, so the debug "none" is not contradicted by mDRM (subject to export completeness, unproven).
- Device: `output/<T>/<date>_setupsession_with_outcome.csv` (`raw_user_agent`, `Platform`) covers 3,777 of the 3,808 attempts. The WebView (`; wv`) split matters for **6001 only**: 1,789 of 1,891
  (94.6%) are wv, 84 non-wv, 18 not in the CSV. It is a correlation, not a proven cause; the 84 non-wv sessions are unexplained.

Unproven: completeness of the mDRM exports (uneven part sizes, widevine ends 22:56, playready 8 rows); that the `fcId` time equals the failure time; the cause of 6001; why 1,958 VSF and 74 EBVS
sessions have no mdrmfe row; the mDRM error body (for example 6211) is not exported.

## Scope guard

In bounds: pure helpers under `investigations/ctap-smvod/scripts/lib/`, one registered Athena query for the cross-day outcome, tests, docs. Out of bounds: changing the existing merge/outcome scripts
or adoption report producers (`src/pipelines/aws_access_cli/scripts/run_adoption_report.py`), live Lightstep calls from scripts. No tenant code or id hardcoded.

## Task overview

- **EM-1** — Pure first-error library over the flat eventdata, mDRM failures and debug states.
- **EM-2** — Cross-day outcome classifier plus the registered Athena query.
- **EM-3** — Cross-check against the error report and the adoption report, with the late-ingest reconciliation line.
- **EM-4** — Outcome × first-error-code report and charts for all seven outcome classes.
- **EM-5** — Docs: `usage.md`, `CONTEXT.md`; unblock PF-8.

## Open questions

- Is the VSF label for a `PLAYER_ERROR`-only session (no `REQUEST_VIEWING` row; 21 on the ZA 2026-10-24 local export, in unified but not Lightstep or debug states) out of scope? Default: out of scope.
- Final names for VPF/VPT and the two no-end classes are open to veto.
- Is the 08:50–08:58 UTC mDRM 403/400 burst (5 sessions, debug 6007) a device-policy event? Unproven.
- Should the mDRM exports gain a request time and `sessionId` on LRM/CDM (export change, manual Lightstep step)? Until then time is the `fcId` prefix.
