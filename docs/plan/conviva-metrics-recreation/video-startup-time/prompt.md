# Video Startup Time — prompt

> Recreate Conviva's Video Startup Time (VST) metric (summary, time series and distribution) from Athena debug events, generically for any tenant and date.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

VST is how long a viewer waits between pressing play and seeing the first frame, and the metric Conviva users watch first when startup feels slow. The repo's metric reference
(`investigations/mtn-monthly-error-code-analysis/docs/conviva-metrics-reference.md`, 2026-10-11) lists the Conviva QoE metrics; the POC on 2026-10-27 showed VST is computable from the debug events we
already hold (`PLAYER_SESSION_EVENT` `CREATE` and the first `PLAYER_STATE_CHANGE` `PLAYING`).

It was studied fourth in the epic's POC-first flow (learn the definition, check local data, build chart and report, finalise with the user). The user accepted the chart, the report and the household
tables on 2026-10-27 ("all data is perfect and the graph is also perfect"), so this story describes the formal build. The scratch POC is evidence for how to do it, not the deliverable. Part of the
`conviva-metrics-recreation` epic; see `../README.md`. It reuses the raw export, session loader, line renderer, breakdown helper and report writer that `../concurrent-plays/` builds (CMR-CP-2,
CMR-CP-6) and must not build them twice.

## Definition implemented

Source: <https://docs.conviva.ai/sei/video/metric-dictionary/video-startup-time/>. Formulas and diagrams, decoded from the page images on 2026-10-27:

- `VST(session)` = `timestamp(playStart)` minus `timestamp(attempt)`. The attempt is the user pressing play (session creation), `playStart` is the first frame.
- With a pre-roll ad: `VST(session)` = (`playStart` minus `attempt`) minus (`preRollAdEnd` minus `preRollAdStart`). Ad startup, ad playback and content pre-fetch during the ad are not counted. With
  SSAI nothing is subtracted, because the ads start after startup completes.
- `VST` = `Average(VST(session))` over the plays starting in the interval. Summary: the average of all plays starting in the period. Time series: each point is the average of the plays starting in
  that interval. Distribution: the number of plays in preset VST ranges (the page does not list the ranges).
- Page adjustments: VST is capped at 600 s per play; plays with a gap or loss of heartbeat during startup are excluded; a missing reading shows as -3; revived sessions do not contribute.
- Related, not part of this story: High Startup Time (HST), the percentage of plays that took too long, driven by an SPI threshold the page does not give.

Rules used by the POC and settled with the user on 2026-10-27:

- **Attempt and play start:** attempt is the session's `CREATE` event; play start is its first `PLAYING` state. Only sessions with both are plays.
- **Bucketing (user decision):** a play is bucketed by its attempt time, UTC day, 5-minute interval by default (an argument).
- **Summary (user decision):** the day value is the average over all plays, not an average of bucket averages; empty buckets are gaps in the chart, not zeros.
- **Cap (user decision):** each play is capped at 600 s; the cap is an argument. A VST below zero is dropped and counted.
- **Not modelled:** pre-roll ads (no ad events exist, assumed absent for VOD), the heartbeat-gap exclusion and revived sessions (no equivalent field), and the -3 "not available" value.
- **Reference figure:** none is held, so no match with Conviva can be claimed and the tolerance stays open. The report must say so. Conviva's reporting timezone is an assumption to verify.

## Result so far (ZA, 2026-10-24, Athena debug events)

POC commits `e52661a` (script and report) and `e8d27d9` (household tables), script `scratch/2026-10-27_conviva-video-startup-time_timeseries_poc.py`, report
`2026-10-24_ZA_video-startup-time-report.md`, chart `output/ZA/charts/2026-10-24_video-startup-time_5min.png` (gitignored, accepted by the user).

| Quantity | Value |
|---|---|
| Sessions in the full-day export | 3,961 |
| Never reached `PLAYING` (not plays) | 2,451 |
| Plays (`CREATE` and `PLAYING`) | 1,510 |
| VST, average | 8.33 s |
| VST, median / 90th percentile | 6.33 s / 14.11 s |
| Plays at the 600 s cap | 1 |
| Households with a play | 445 |

Cross-check: the `startup_time_ms` column of `session.csv` (the Athena `REQUEST_VIEWING` event) equals the debug-event delta on all 1,505 plays that have a value (zero difference). Over all 3,791
sessions that have a value it averages 6.85 s, because sessions that never played carry a value too, so it is not Conviva's VST on its own. The chart has two spikes of about 72 s (07:20 UTC) and 78 s
(20:50 UTC) in 5-minute buckets, not yet explained. The distribution ranges in the POC are the POC's own, not Conviva's. No Conviva reference number is held yet.

Data used: `investigations/ctap-smvod/data/athena/ZA/2026-10-24_debug_all_events.csv`, `2026-10-24_session.csv` (content, household, `startup_time_ms`), the parsed user-agent
`output/ZA/2026-10-24_setupsession_with_outcome.csv` and the Lightstep mDRM exports for device type. The POC reuses the concurrent plays POC readers by import; the formal build shares them instead of
copying.

## Scope guard

In bounds: the story folder, `scratch/` until graduation, and the `investigations/conviva-metrics/` folder that `../concurrent-plays/` scaffolds (CMR-CP-2), for the VST script, its pure module and its
report writer. Shared code goes in `src/lib/`, and only through the helpers `../concurrent-plays/` (CMR-CP-6) builds: session loader, line renderer, breakdown/top-content helper and report writer. New
Athena queries are needed only if a gap task (CMR-VST-4) finds a missing field.

Out of bounds: the other metrics' stories and the placeholder sub-stories, `investigations/ctap-smvod/scripts/`, High Startup Time (a follow-up story, see below), and re-implementing anything
`../concurrent-plays/` already owns. Read-only on Athena; resolve the tenant with `python scripts/resolve_tenant.py ...` first (`docs/guides/tenant-resolution.md`). Everything stays tenant- and
date-agnostic: arguments, with per-tenant state names as the documented mapping CMR-CP-6 defines.

**Execution order:** CMR-VST-1 needs no data and can run now. CMR-VST-2 reads the local ZA export. CMR-VST-3 and the data side of CMR-VST-4 need `../concurrent-plays/` CMR-CP-2 (raw export for any
tenant and date). CMR-VST-5 (graduation) needs CMR-CP-6 (shared helpers) and its own go-ahead.

## Session-start load hints

`../discussion-prompt.md` (Discussion log); `../cir-related-exits/`, `../concurrent-plays/` and `../attempts/` as the patterns; `scratch/SCRATCH.md`; `docs/guides/chart-guidelines.md`;
`docs/guides/query-catalog.md`; `docs/refactor/planning-protocol.md`, `design-principles.md` and `code-deduplication-and-taxonomy.md`; `docs/guides/project-taxonomy.md` and
`functional-code-taxonomy.md`; the POC script's header.

## Task overview

- **CMR-VST-1** — Settle the open definition points and the report content (a discussion session with the user)
- **CMR-VST-2** — Explain the number: the two chart spikes, plays without a `CREATE`, `startup_time_ms` against the debug-event delta
- **CMR-VST-3** — Prove the POC generalises: run it for another tenant and another date
- **CMR-VST-4** — Close the data gaps: Conviva's distribution ranges, heartbeat gap and pre-roll rules, device and playback type
- **CMR-VST-5** — Formal recreation: graduate the POC into tested code (separate go-ahead)

## Definition of done

All of CMR-VST-1 to CMR-VST-5 are complete, and the VST number for the reference tenant and day is either matched to Conviva or the gap is explained.

## Perspectives not covered

High Startup Time (a follow-up story on the same pure VST module: share of plays over an SPI threshold, which the user must supply), startup time split by phase (manifest, DRM licence, first segment),
breakdown by dimension (ISP, player, CDN), real-time buckets, linear playback (the local ZA data is VOD-only), and a per-device or per-content distribution chart.
