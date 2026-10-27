# Concurrent Plays — prompt

> Recreate Conviva's Concurrent Plays metric (summary and time series) from Athena debug events, generically for any tenant and date.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Concurrent Plays is the audience-size metric that Conviva shows next to Attempts, and it is the one most sensitive to how a session's playing time is defined. It was studied second in the epic's
POC-first flow (learn the definition, check local data, fetch gaps, produce chart and report, finalise with the user). The user accepted the chart on 2026-10-27, so this story now describes the formal
build. The scratch POC is evidence for how to do it, not the deliverable. Part of the `conviva-metrics-recreation` epic; see `../README.md`. It supersedes the concurrent-plays half of the placeholder
`../attempts-concurrent-plays/`, which is left untouched.

## Definition implemented

Source: <https://docs.conviva.ai/sei/video/metric-dictionary/concurrent-plays/> (page updated 2026-09-23). Formulas, supplied by the user as images on 2026-10-27:

- `concurrentPlay` (per session, per 60-second data bucket) = the sum of the active sessions with at least one video frame in the bucket.
- `Concurrent Plays` = the maximum of `concurrentPlay` over the selected time interval.

Rules from the page: a session counts only after its video has started playing; rebuffering, pause and other trick modes are not counted; unsuccessful attempts are excluded; each bucket aggregates the
previous 60 seconds; an hourly interval has 60 buckets and a daily one 1,440; aggregated time-series points are 15-minute maxima; the summary is the maximum over the period. Conviva notes 1-2%
variance between minute, hourly and daily granularities. The page does not state the inactivity limit for stale sessions.

Rule settled with the user in CMR-CP-1 (2026-10-27): a session is playing from a `PLAYER_STATE_CHANGE`/`PLAYING` event until the next `BUFFERING`, `PAUSED`, `STOPPED` or `DESTROY` state, or a
`PLAYER_SEEK`, `PLAYER_EOF` or `PLAYER_ERROR` event. It counts in every UTC minute that overlaps its playing time.

- **Open intervals:** an interval still open at the session's last event ends at that event (default). The timeout is an argument; 300 s is the sensitivity check, since Conviva's inactivity limit is
  not published.
- **Ties:** on equal timestamps, closing events sort before `PLAYING`.
- **Day and buckets:** UTC day, minute buckets from 00:00 UTC. Assumption to verify: Conviva's reporting timezone for the customer.
- **Reference figure:** none is held, so no match with Conviva can be claimed and the match tolerance stays open until a figure exists. The report must say so.

## Result so far (ZA, 2026-10-24, Athena debug events)

POC commit `1bcb06e`, script `scratch/2026-10-27_conviva-concurrent-plays_timeseries_poc.py`, chart `output/ZA/charts/2026-10-24_concurrent-plays_15min.png` (gitignored, accepted by the user).

| View | Peak | Minute (UTC) |
|---|---|---|
| Playing time, unclosed end = last event (headline) | 16 | 07:53 |
| Playing time, unclosed end = last event + 300 s | 16 | 07:53 |
| Playing time on the local `debug_states.csv` | 16 | 07:53 |
| Whole session alive (first to last event), for comparison only | 24 | 17:36 |

Of 3,961 sessions in the full-day export, 1,511 reached `PLAYING`, 2,450 never played and are excluded, and 142 played sessions end with the playing interval still open. At the peak minute 7 of the 16
sessions were one title. No Conviva reference number is held yet. The report is `2026-10-24_ZA_concurrent-plays-report.md`; its content was settled in CMR-CP-1 (see `stories.md`).

Data inventory for the day: `data/athena/ZA/2026-10-24_debug_eventid_inventory.csv` (event ids and states with counts). The Athena table `unified_e6auj7k7.e6auj7k7_ccl_debug_events` has a raw JSON
`eventdata` column (for example `{"state":"PLAYING","position":0,"sessionid":"abr-vod-..."}`); the catalog query `ctap-smvod-debug-states` extracts only a few fields and filters five event ids, so it
drops `PLAYER_SEEK`, `PLAYER_EOF` and `PLAYER_BUFFER_LEVEL`.

## Scope guard

In bounds: the story folder, `scratch/` until graduation, the new catalog query and its saved exports, and (at CMR-CP-6 only) `scripts/dev/` and `src/lib/charts/`. Out of bounds: `investigations/`
scripts such as `compute_concurrent_playback.py` (a different, whole-session view; do not edit), and the placeholder sub-stories. Read-only on Athena; resolve the tenant with `python
scripts/resolve_tenant.py ...` first (`docs/guides/tenant-resolution.md`). Everything stays tenant- and date-agnostic: arguments, with per-tenant state names as a documented mapping.

## Session-start load hints

`../discussion-prompt.md` (Discussion log); `../attempts/` as the pattern; `scratch/SCRATCH.md`; `docs/guides/chart-guidelines.md`; `docs/guides/query-catalog.md`; `docs/refactor/planning-protocol.md`
and `design-principles.md`; `docs/guides/project-taxonomy.md`; the POC script's header.

## Task overview

- **CMR-CP-1** — Settle the definition points and decide the report content (a discussion session with the user)
- **CMR-CP-2** — Download the full-day raw debug events (with `eventdata` as stored) through a catalogued query
- **CMR-CP-3** — Explain the differences: open playing intervals, sessions outside `session.csv`, playing versus alive
- **CMR-CP-4** — Prove the POC generalises: run it for another tenant and another date
- **CMR-CP-5** — Close the data gaps: device type and linear versus VOD
- **CMR-CP-6** — Formal recreation: graduate the POC, renderer, report and data queries (separate go-ahead)

## Definition of done

All of CMR-CP-1 to CMR-CP-6 are complete, and the Concurrent Plays number for the reference tenant and day is either matched to Conviva or the gap is explained.

## Perspectives not covered

Real-time 10-second buckets, breakdowns by dimension (ISP, player), the hourly and daily granularity variance Conviva mentions, and cross-tenant deduplication.
