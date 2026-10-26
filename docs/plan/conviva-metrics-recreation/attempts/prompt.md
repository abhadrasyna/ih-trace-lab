# Attempts — prompt

> Recreate Conviva's Attempts metric (summary and time series) from local Athena data, generically for any tenant and date.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Attempts is the denominator for most Conviva ratios (VSF, VPF, EBVS), so it has to be right before the failure metrics mean anything. The epic method (decided 2026-10-26) is to read Conviva's
documentation per metric and build a `scratch/` POC to see how far local data gets. This story records that POC for attempts, which was done first and in one sitting (ZA, 2026-10-24), and the open
questions it left. It supersedes the attempts half of the placeholder `../attempts-concurrent-plays/`, which stays in place for concurrent plays and is left untouched. Part of the
`conviva-metrics-recreation` epic; see `../README.md`.

## Definition implemented

Source: <https://docs.conviva.ai/sei/video/metric-dictionary/attempts/> (page updated 2026-09-02). Attempts counts the times viewers attempted to start playback in the interval. It is a "Started"-type
metric shown as a summary and a time series; each time-series point is the attempts in that interval, and the summary is the sum of the points. Whether auto-play counts depends on the player
integration. Revived sessions that play successfully also count toward Attempts (but not VST, EBVS or VSF). The formula on the page is an image (`equation34_attempts.svg`) and is not yet captured.

Working assumption, to verify (CMR-ATT-5): one attempt is one distinct `sessionId` with a `PLAYER_SESSION_EVENT` / `CREATE` event, bucketed by that event's UTC time.

## Result so far (ZA, 2026-10-24, local data only)

| Source | Sessions |
|---|---|
| `athena/ZA/2026-10-24_debug_states.csv`, CREATE events (the chart) | 3,901 |
| `athena/ZA/2026-10-24_session.csv` | 3,797 (138 CREATE sessions absent; 34 of its sessions have no CREATE that day) |
| `athena/ZA/2026-10-24_outcome_first_debug.csv` | 3,808 (140 CREATE sessions absent) |
| `lightstep/ZA/2026-10-24_smvod.csv` | 4,443 (all CREATE sessions present; about 540 extra) |

The chart is `output/ZA/charts/<date>_attempts_5min.png` (gitignored), produced by `scratch/2026-10-26_conviva-attempts_timeseries_poc.py` with the scratch renderer `scratch/_lib/line_chart.py`.

## Scope guard

Scratch scripts only, under `scratch/`, until the graduation task (CMR-ATT-7), which needs its own go-ahead. Read-only, local data first; fetch from Lightstep or Athena only for a gap local data
cannot close, after `python scripts/resolve_tenant.py ...` per `docs/guides/tenant-resolution.md`. Everything must stay tenant- and date-agnostic (argparse arguments, documented mappings).

## Session-start load hints

`../discussion-prompt.md` (Discussion log); `scratch/SCRATCH.md`; `docs/guides/chart-guidelines.md`; `docs/guides/query-catalog.md`; the POC script's header.

## Task overview

- **CMR-ATT-1** — Done: POC script, per-interval attempts from CREATE events with reconciliation counts
- **CMR-ATT-2** — Done: chart on the shared theme, with the scratch line renderer
- **CMR-ATT-3** — Done: chart header streamlined (title, KPI, footer); chart accepted as final
- **CMR-ATT-4** — Explain the 138-140 CREATE sessions missing from Athena exports and the extra Lightstep sessions
- **CMR-ATT-5** — Settle the open definition points: formula, reference number, day boundary, auto-play and revived sessions
- **CMR-ATT-6** — Prove the POC generalises: run it for another tenant and another date
- **CMR-ATT-7** — Graduate the POC and the line renderer (separate go-ahead)

## Definition of done

All of CMR-ATT-1 to CMR-ATT-7 are complete, and the attempts number for the reference tenant and day is either matched to Conviva or the gap is explained.

## Perspectives not covered

Concurrent plays (stays in `../attempts-concurrent-plays/`), breakdowns by dimension (ISP, player), and cross-device or cross-tenant deduplication.
