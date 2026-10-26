# Session lifecycle report (ctap-smvod) — prompt

> A daily, per-tenant summary that follows every session from setup to its outcome: which hops it reached, where it stopped, how long each hop took, and which cohorts fail, with charts a non-expert
> can read.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The epic goal is to follow one `sessionId` from creation (`sm-vod` / `sm-linear`) through every hop to where it succeeds or fails, and to tell that story every day for every tenant.
`session-error-model/` defines the outcome and the first error, `session-presence-funnel/` PF-8 builds the per-session trace matrix and PF-4 the daily trend. What is still missing is the lifecycle
layer on top: the furthest hop, the path, the time between hops, the cohort view, an export-completeness gate, and one daily summary per tenant that ties the charts together. A read-only review on
2026-10-26 (ZA 2026-10-24, local exports) showed why it matters: the largest loss is between debug CREATE and the licence request (1,997 of 3,808 attempts, 96% VSF), not at mDRM (5 sessions).

## Scope guard

Changes runtime behaviour: new scripts, a pipeline step and generated outputs under `output/<TENANT>/session-lifecycle/`. Does not change the outcome or first-error rules (imported from
`session-error-model/`), the PF-8 matrix it reads, or any existing report; the existing `output/<TENANT>/drm-analysis/` reports stay as they are and are only linked. Generic by design: no tenant code
or id in scripts or tests; tenant data comes from `config/tenants.yaml` (`shared_project`, `disambiguation_attribute`, presence of `mdrm_tenant_id`). A tenant without mDRM fields (NG today) gets a
report without mDRM hops, not zeros. Lightstep exports stay manual; scripts never call Lightstep.

Decisions carried from the epic (keep): no per-error-code charts or splits; device attributes (`is_wv`, DRM type, CDM security level) are reported per outcome as associations, not causes; outcome
names come from `session-error-model/prompt.md` and are not redefined here; every count is a snapshot and carries its export time.

## Session-start load hints

- `../README.md` — hop order, cross-cutting constraints (completeness status, UTC day, minimum n).
- `../session-error-model/prompt.md` — outcome classes, first-error rule, EM-4 charts.
- `../session-presence-funnel/stories.md` — PF-4 trend upsert, PF-8 matrix columns and charts.
- `docs/guides/chart-guidelines.md` — chart rules and the `src/lib/charts` inventory.
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — mDRM export conventions, parts, fcId time.
- `investigations/ctap-smvod/scripts/lib/{drm_exports.py,drm_funnel.py,webview.py,funnel_stages_chart.py}` — readers, `session_kind`, `is_wv`, funnel chart.

## Evidence (ZA 2026-10-24; Lightstep exports 2026-10-26 06:31–06:44 IST, Athena local 07:07–07:08, live outcomes 17:39)

Furthest hop of the 3,808 attempts: no debug event (local) 33; debug CREATE only, no licence request 1,997 (VSF 1,927, EBVS 70); LRM 2; CDM without playback 271 (VSF 131, EBVS 140); playback started
1,505 (success 1,187, VPT 227, VPF 80, no-end 9, EBVS 2 — EBVS with PLAYING in debug is an inconsistency to check).

Hop timing (p5 / p50 / p95 s): setup → CREATE −1.7 / −0.07 / 0.8 (n 2,195); CREATE → mdrmfe (fcId proxy) 0.0 / 2.3 / 13.0 (n 1,793); CREATE → first debug error for VSF 0.6 / 2.1 / 11.7 (n 2,059); for
VPF 38 / 96 / 1,149 (n 80).

Cohorts (associations): WebView 1,871 attempts, 2 reach mdrmfe, 99.3% non-success; non-WebView 1,906, 1,744 reach mdrmfe, 38.9% non-success. Widevine L1 922 sessions 40.2% non-success (127 VSF); L3
642 sessions 25.1% (2 VSF). VSF households are not concentrated (top 10 hold 13.3%).

Per-tenant data shape (2026-10-21..24): ZA ~4,000–4,600 VOD sessions a day, no linear. GH ~200–800 VOD sessions a day plus a large linear share (31–35% of CTAP traces have no sm-vod setup; mdrmfe rows
split 1,767 `abr-linear-` / 2,102 `abr-vod-`). ZM ~100–200 VOD sessions a day, ~10% linear. GH and ZM share one Lightstep project (`busUnitId` separates them).

## Task overview

- **SL-1** — Export completeness check per tenant, date and export kind.
- **SL-2** — Lifecycle columns on top of the PF-8 matrix: furthest hop, path, hop timestamps and latencies, cohorts.
- **SL-3** — Daily per-tenant summary markdown with charts and generated explanations.
- **SL-4** — Daily pipeline step and lifecycle trend upsert for every tenant with exports.
- **SL-5** — Exploratory sankey and per-session timeline prototypes in `scratch/`.
- **SL-6** — Validate on ZA, then GH and ZM after LC-2; NG onboarding note; docs and `CONTEXT.md`.

## Definition of done

For any tenant and date with exports, `run_pipeline.py` writes `output/<TENANT>/session-lifecycle/<date>_summary.md` with its charts and CSVs, a completeness status, and a trend row; ZA 2026-10-24
reproduces the evidence above within the late-ingest tolerance. See `tasks.md` "Story done when".

## Analyses and their standing (2026-10-26)

| Analysis | Standing | Reason |
|---|---|---|
| Drop-off by hop, path patterns | Proven | Every hop has a direct join (LRM/CDM via fcId) |
| Time to failure (debug) | Proven | Debug event times |
| mDRM hop timing | Proxy | Only the fcId hex prefix (median +2.3 s vs CREATE); no span timestamp exported |
| Device, DRM type, security level by outcome | Proven as association | Not a cause |
| Household concentration | Proven, not concentrated | Top 10 hold 13.3% of VSF |
| Repeat licence requests per session | Counts proven, meaning unproven | 1,964 one, 133 two, 51 three |
| Hour of day | Exploratory | Hour 23 has n=25, possibly late ingest |
| Content | Exploratory | Top 10 hold 39% of VSF, confounded with device |
| Crossed midnight | Needs EM-2 look-ahead | Only 2 known |
| Setup latency | Partial | `smvod-ts` cap leaves setup times for 56% of sessions |
| CDN/segment hop, mDRM error reason, cause of WebView failure | Not supportable | Not in any export |

## Open questions (append answers here)

- Minimum n for showing a rate: default 30 (a report parameter); confirm or change.
- Outcome names (VPF/VPT, no-end classes) are open to veto in `session-error-model/`.
- The 529 (live) / 542 (local) Lightstep sessions not observed in Athena: PF-7b owns them; this report shows them as a path, not a loss.
- The ZA 2026-10-21 step change: the WebView share of sessions went from 35% (10-20) to 69% (10-21); about 89% of the added sessions were WebView. Observation only.
- Export requests (manual Lightstep step): a span timestamp on the mDRM exports, `sessionId` on LRM and CDM, and splits that keep `smvod-ts` and CDM parts under their caps.

## Perspectives not covered

- Linear outcomes are not checked until LC-2 lands; until then GH and ZM reports show linear sessions only as an mDRM-side count with a "linear not covered" banner.
- No CDN, manifest or segment hop: there is no export for it.
- Sankey and timeline helpers are not added to `src/lib/charts` by this story; SL-5 only prototypes them.
