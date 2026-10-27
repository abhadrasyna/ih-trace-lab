# CIR Related Exits — prompt

> Recreate Conviva's CIR Related Exits metric (summary and time series) from Athena debug events, generically for any tenant and date.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

CIR Related Exits tells us how often a viewer leaves right after a stall that was not caused by a seek, so it is the closest Conviva metric to "buffering made them quit". The repo's metric reference
(`investigations/mtn-monthly-error-code-analysis/docs/conviva-metrics-reference.md`, 2026-10-11) marked it "computable: no" because it needs seek events. The POC on 2026-10-27 showed it is computable
from the debug events we already hold (`PLAYER_STATE_CHANGE`, `PLAYER_SEEK`, `DESTROY`, `PLAYER_ERROR`).

It was studied third in the epic's POC-first flow (learn the definition, check local data, build chart and report, finalise with the user). The user accepted the chart and report on 2026-10-27, so
this story describes the formal build. The scratch POC is evidence for how to do it, not the deliverable. Part of the `conviva-metrics-recreation` epic; see `../README.md`. It reuses the raw export,
session loader, line renderer, breakdown helper and report writer that `../concurrent-plays/` builds, and must not build them twice.

## Definition implemented

Source: <https://docs.conviva.ai/sei/video/metric-dictionary/cir-related-exits/> (page updated 2026-09-23). Formulas and diagrams, decoded from the page images on 2026-10-27:

- `CIRRelatedExit(session)` = 1 when the session is an ended play and CIR occurred within 5 seconds of the session end, else 0.
- `CIR Related Exits` = `sum(CIRRelatedExit)` divided by `sum(endedPlay)` over the interval (a ratio, shown with the count).
- CIR (connection-induced rebuffering) is a stall not related to a seek. Rebuffering after a seek is seek rebuffering and is non-CIR time.
- The CIR impact period counts back from the session end until 30 seconds of cumulative non-CIR time, or the play start; session CIR time (the distribution value) is the CIR inside that period. In the
  page's example, 20 s playing, 9 s playing and 1 s of a 10 s seek rebuffer make the 30 s, and CIR time is 10 s + 2 s = 12 s.
- Page adjustments: application backgrounding may count as a session end; for a session under 30 s all rebuffering counts. The metric is not available for CDN dimensions, and only for ended sessions.
- The page does not give the seek-grace rule. The 10 s rule comes from Conviva's CIRR page (rebuffering that starts 10 s or more after a seek ends is connection induced), applied here by user
  decision.

Rules used by the POC and settled with the user on 2026-10-27:

- **Ended play:** a session with at least one `PLAYING` state and a terminal `DESTROY`, `STOPPED` or `PLAYER_ERROR` event after it. Errors count as ended plays. The session end is the first terminal
  event.
- **Stall:** `BUFFERING` after the first `PLAYING`, until the next `PLAYING` or `PAUSED`, or the session end if still open. The startup `BUFFERING` before the first `PLAYING` is not a stall.
- **CIR:** a stall that does not start within 10 s after a `PLAYER_SEEK` (`PLAYER_SEEK` carries only a start time, so the grace runs from it).
- **Exit flag:** a CIR stall overlaps the last 5 s before the session end; a stall still open at the end counts. Window and grace are arguments.
- **Day and buckets:** UTC day, a play is bucketed by its end time; 5 minutes by default, an argument. Assumption to verify: Conviva's reporting timezone.
- **Reference figure:** none is held, so no match with Conviva can be claimed and the tolerance stays open. The report must say so.
- **Not modelled yet:** the 30 s impact period and CIR-time distribution, the 90 s expiry from the secondary summary, sessions under 30 s, backgrounding as a session end (CMR-CIR-1).

## Result so far (ZA, 2026-10-24, Athena debug events)

POC commit `38d767c`, script `scratch/2026-10-27_conviva-cir-related-exits_timeseries_poc.py`, report `2026-10-24_ZA_cir-related-exits-report.md`, chart
`output/ZA/charts/2026-10-24_cir-related-exits_5min.png` (gitignored, accepted by the user).

| Quantity | Value |
|---|---|
| Sessions in the full-day export | 3,961 |
| Never reached `PLAYING` (not ended plays) | 2,450 |
| Played but no terminal event (not ended plays) | 181 |
| Ended plays | 1,330 |
| CIR related exits | 258 |
| CIR Related Exits | 19.40% |

Of the 258 exits, 244 were on mobile Android / Chrome and all were VOD. The per-5-minute series is noisy (about 5 ended plays per bucket), so the interval is revisited in CMR-CIR-1. No Conviva
reference number is held yet.

Data used: `investigations/ctap-smvod/data/athena/ZA/2026-10-24_debug_all_events.csv` (event ids and states in `2026-10-24_debug_eventid_inventory.csv`). The POC reuses the concurrent-plays POC
readers by import; the formal build shares them instead of copying.

## Scope guard

In bounds: the story folder, `scratch/` until graduation, and the `investigations/conviva-metrics/` folder that `../concurrent-plays/` scaffolds (CMR-CP-2), for the CIR script, its pure module and its
report writer. Shared code goes in `src/lib/`, and only through the helpers `../concurrent-plays/` (CMR-CP-6) builds: session loader, line renderer, breakdown/top-content helper and report writer. New
Athena queries are needed only if a gap task (CMR-CIR-4) finds a missing field.

Out of bounds: the other metrics' stories and the placeholder sub-stories, `investigations/ctap-smvod/scripts/`, and re-implementing anything `../concurrent-plays/` already owns. Read-only on Athena;
resolve the tenant with `python scripts/resolve_tenant.py ...` first (`docs/guides/tenant-resolution.md`). Everything stays tenant- and date-agnostic: arguments, with per-tenant state names as the
documented mapping CMR-CP-6 defines.

**Execution order:** CMR-CIR-1 needs no data and can run now. CMR-CIR-2 reads the local ZA export. CMR-CIR-3 and the data side of CMR-CIR-4 need `../concurrent-plays/` CMR-CP-2 (raw export for any
tenant and date). CMR-CIR-5 (graduation) needs CMR-CP-6 (shared helpers) and its own go-ahead.

## Session-start load hints

`../discussion-prompt.md` (Discussion log); `../concurrent-plays/` and `../attempts/` as the patterns; `scratch/SCRATCH.md`; `docs/guides/chart-guidelines.md`; `docs/guides/query-catalog.md`;
`docs/refactor/planning-protocol.md`, `design-principles.md` and `code-deduplication-and-taxonomy.md`; `docs/guides/project-taxonomy.md` and `functional-code-taxonomy.md`; the POC script's header.

## Task overview

- **CMR-CIR-1** — Settle the open definition points and the report content (a discussion session with the user)
- **CMR-CIR-2** — Explain the number: open stalls at the end, plays with no end event, seek proximity, sample sessions
- **CMR-CIR-3** — Prove the POC generalises: run it for another tenant and another date
- **CMR-CIR-4** — Close the data gaps: backgrounding as a session end, device type and playback type
- **CMR-CIR-5** — Formal recreation: graduate the POC into tested code (separate go-ahead)

## Definition of done

All of CMR-CIR-1 to CMR-CIR-5 are complete, and the CIR Related Exits number for the reference tenant and day is either matched to Conviva or the gap is explained.

## Perspectives not covered

The CIR-time distribution as a chart, CIRR and CIRT (they share the stall and seek logic and would be a follow-up story on the same stall module), breakdown by dimension (ISP, player, CDN, which
Conviva does not offer for this metric), real-time buckets, and linear playback, which the local ZA data does not contain.
