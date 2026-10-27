# Video Start Failures Technical — prompt

> Recreate Conviva's Video Start Failures Technical (VSF-T) metric (summary, time series and per-error-code detail) from Athena debug events and the error eventdata, generically for any tenant and
> date.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

VSF-T is the share of play attempts that failed to start because of a technical player error. It is the failure number that matters most for the ZA tenant: the POC on 2026-10-27 found that more than
half of all attempts on 2026-10-24 fail to start, and about 90% of those carry one error, 6001. The repo's metric reference
(`investigations/mtn-monthly-error-code-analysis/docs/conviva-metrics-reference.md`) lists the Conviva QoE metrics, and the POC showed VSF-T is computable from the debug events we already hold
(`PLAYER_ERROR` before the first `PLAYING` state) plus the flattened error eventdata for the per-code detail.

It was studied fifth in the epic's POC-first flow (learn the definition, check local data, build chart and report, finalise with the user). The user approved the layout in
`2026-10-24_ZA_vsf-technical-error-summary-optionA.md` on 2026-10-27 as the final form, so this story describes the formal build of that report. The scratch POCs are evidence for how to do it, not the
deliverable. Part of the `conviva-metrics-recreation` epic; see `../README.md`. It reuses the raw export, session loader, line renderer, breakdown helper and report writer that `../concurrent-plays/`
builds (CMR-CP-2, CMR-CP-6) and must not build them twice. It takes over the VSF half of the placeholder `../vpf-vsf/` (see the scope guard).

## Definition implemented

Source: <https://docs.conviva.ai/sei/video/metric-dictionary/video-start-failures-technical/> (the VSF-B page was read alongside it). The page text, read on 2026-10-27:

- A session counts as a video start failure when it ends or fails to start because of a fatal player error. VSF-T counts the ones with a technical error; VSF-B counts the ones whose error matches the
  business-error list the customer maintains.
- An error followed by successful play does not count. A start that ends without any error is an exit before video start (EBVS), not a failure.
- VSF-T is counted at the time of the failure and reported as a count and as a percentage of Attempts.

Rules used by the POC (`scratch/2026-10-27_conviva-vsf-technical_timeseries_poc.py`):

- **Attempt:** a distinct session id with a `CREATE` event on the date (3,954 sessions on the ZA day).
- **Start failure:** a `PLAYER_ERROR` before the first `PLAYING` state and before `DESTROY`. An error after `DESTROY` is not a failure (Conviva may count one within 90 s; to verify). On equal
  timestamps an error sorts before `PLAYING`.
- **Bucketing:** a failure is bucketed at its first error, in UTC, 5-minute buckets by default (an argument); the day value is the total over all buckets.
- **Classification (user decision, 2026-10-27):** every failure is VSF-T for now. `--business-codes` holds the business list and defaults to empty; a session with any business code before start is
  VSF-B. The real business-error list (MEC-27) does not exist yet and will change the split later.
- **Not modelled:** the 200 ms rule and revived sessions (no equivalent field), and Conviva's 90 s late-error window.
- **Reference figure:** none is held, so no match with Conviva can be claimed and the tolerance stays open. The report must say so. Conviva's reporting timezone is an assumption to verify.

## Report layout approved on 2026-10-27

The target is `2026-10-24_ZA_vsf-technical-error-summary-optionA.md`. Option B (a one-row-per-code summary plus the same detail tables) is evidence of the choice and is not built.

1. Title, one-paragraph definition with the Conviva link, and the chart (5-minute series).
2. Headline: VSF-T count, share of attempts, VSF-B count, peak bucket.
3. Error codes table, one row per code (top 10; a session with several codes counts under each, so rows do not add up): VSF-T sessions, % of VSF-T, % of attempts, impacted households, % of all
   households, sessions per household, first and last failure (UTC). A note gives the household total and the sessions with no household.
4. Top 10 content, playback type.
5. Error code detail: one table per main code (6001, 3016, 1003, E31012) with parallel column pairs separated by a blank spacer column. Columns: player phase, network type, a code-specific third pair
   (WebView for 6001 only, pipeline status for 3016, host for 1003), and estimated bandwidth bands (under 1, 1 to 3, 3 to 10, over 10 Mbps, plus a "no data" row). Shaka error text and bandwidth
   percentiles sit under the table. Sessions are grouped by first error; 3016's three spellings of `PIPELINE_ERROR_DECODE` are merged.

Open about this layout, settled in CMR-VSFT-1: the bandwidth bands and measure (Shaka `estimatedbandwidth`) are the POC's guess; which codes get a detail table once the code list changes; whether the
chart image is committed beside the report.

## Result so far (ZA, 2026-10-24, Athena debug events)

POC commit `005e774` (script and report), summary previews `fcb5b71` and `09346c7`, bandwidth script and chart `09aa839`, spacer columns `c15c2fc`, extended error-codes table `a5d8043` and `10a590a`.
Scripts `scratch/2026-10-27_conviva-vsf-technical_timeseries_poc.py`, `..._error-bandwidth_poc.py` and `..._error-codes-table_poc.py`. Report `2026-10-24_ZA_vsf-technical-error-summary-optionA.md`
(the earlier `2026-10-24_ZA_vsf-technical-report.md` is the first, shorter form). Chart `2026-10-24_ZA_vsf-technical_5min.png`, copied from the gitignored `output/ZA/charts/`.

| Quantity | Value |
|---|---|
| Attempts (sessions with `CREATE`) | 3,954 (the attempts POC's `debug_states.csv` gives 3,901; unresolved) |
| VSF-T (all failures; no business list) | 2,101 (53.1% of attempts); VSF-B 0 |
| Peak 5-minute bucket | 32 at 09:15 UTC |
| Sessions with a flat error row | 2,085 of 2,101 |
| Error 6001 (first error) | 1,887 sessions; 1,898 counting every code; 358 households, 5.3 sessions each |
| Error 3016 / 1003 / E31012 (first error) | 104 / 29 / 7 sessions |
| Other first-error codes | 58 sessions |
| Households (all attempts / VSF-T sessions without one) | 865 / 22 |

Cross-check: `outcome_first_debug.csv` marks 2,091 sessions `VSF`; all of them are in the POC's 2,101, and the POC adds 10 more that the older file does not count.

What the detail shows: 6001 is always a `DRM.REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE` Shaka error in the `LOADING` phase, on 4g in 99.6% of sessions and in a WebView in 94.3%; its events carry no
Shaka stats, so it has no bandwidth data. 3016 is a decode error (`PIPELINE_ERROR_DECODE`) while seeking in 96% of sessions, with bandwidth data for 103 of 104. 1003 splits between SSAI and CDN hosts
and has bandwidth data for 11 of 29. E31012 is an app-level timeout with no Shaka error and bandwidth data for 5 of 7.

## Input inventory (reused, enhanced, new)

| Input | Status | Notes |
|---|---|---|
| Raw debug events, full day (`<date>_debug_all_events.csv`) | **reuse**; formal source is the CMR-CP-2 raw export | the POC reads the parsed CSV |
| `session.csv` (content, `householdId`) | **reuse** the CMR-CP-6 session loader | household counts depend on it |
| Flattened error eventdata (`flatten_error_eventdata.py`) | **enhance**: a saved export per tenant and date with a runner (CMR-VSFT-4) | phase, network, WebView, host, status, Shaka stats |
| Business-error list (MEC-27) | **new**, blocked on the user | drives the VSF-T and VSF-B split |
| Bandwidth bands | **new** pure function over the flat export | bands are the POC's guess |
| Linear and device splits | **reuse** CMR-CP-5 sources | the ZA data is VOD only |

## Scope guard

In bounds: the story folder, `scratch/` until graduation, and the `investigations/conviva-metrics/` folder that `../concurrent-plays/` scaffolds (CMR-CP-2), for the VSF-T script, its pure module and
its report writer. Shared code goes in `src/lib/`, and only through the helpers `../concurrent-plays/` (CMR-CP-6) builds: session loader, line renderer, breakdown/top-content helper and report writer.
New Athena queries are needed only if a gap task (CMR-VSFT-4) finds a missing field.

Out of bounds: the other metrics' stories and the placeholder sub-stories (the `../vpf-vsf/` placeholder is left as is; its VPF half and the shared error taxonomy stay there), the
`investigations/ctap-smvod/scripts/` tools (read-only; the flattener is wrapped, not edited), the error classification of business errors beyond the configurable list, and re-implementing anything
`../concurrent-plays/` already owns. Read-only on Athena; resolve the tenant with `python scripts/resolve_tenant.py ...` first (`docs/guides/tenant-resolution.md`). Everything stays tenant- and
date-agnostic: arguments, with per-tenant state names as the documented mapping CMR-CP-6 defines.

**Execution order:** CMR-VSFT-1 needs no data and can run now. CMR-VSFT-2 reads the local ZA export. CMR-VSFT-3 and the data side of CMR-VSFT-4 need `../concurrent-plays/` CMR-CP-2 (raw export for any
tenant and date). CMR-VSFT-5 (graduation) needs CMR-CP-6 (shared helpers) and its own go-ahead.

## Session-start load hints

`../discussion-prompt.md` (Discussion log); `../video-startup-time/`, `../cir-related-exits/` and `../concurrent-plays/` as the patterns; `scratch/SCRATCH.md`; `docs/guides/chart-guidelines.md`;
`docs/guides/query-catalog.md`; `docs/refactor/planning-protocol.md`, `design-principles.md` and `code-deduplication-and-taxonomy.md`; `docs/guides/project-taxonomy.md` and
`functional-code-taxonomy.md`; the three scratch scripts' headers; `investigations/ctap-smvod/scripts/flatten_error_eventdata.py`.

## Task overview

- **CMR-VSFT-1** — Settle the open definition points and the report content (a discussion session with the user)
- **CMR-VSFT-2** — Explain the number: attempts 3,954 against 3,901, the 10 extra sessions against `outcome_first_debug.csv`, the 16 sessions with no flat error row, multi-code sessions and the 6001
  repeat households
- **CMR-VSFT-3** — Prove the POC generalises: run it for another tenant and another date
- **CMR-VSFT-4** — Close the data gaps: the business-error list, a saved flat error export per tenant and date, bandwidth for 6001, device and playback type
- **CMR-VSFT-5** — Formal recreation: graduate the POCs into tested code and the option A report (separate go-ahead)

## Definition of done

All of CMR-VSFT-1 to CMR-VSFT-5 are complete, and the VSF-T number for the reference tenant and day is either matched to Conviva or the gap is explained.

## Perspectives not covered

VSF-B as its own report once the business-error list exists (the formal code already splits by the list), a VSF-T time series per error code, breakdown by dimension (ISP, player, CDN, app version),
real-time buckets, linear playback (the local ZA data is VOD-only), Conviva's late-error window (errors within 90 s of a failure), and the link to exits before video start (the `../ebvs/` story).
