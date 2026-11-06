# Shaka 6001 ZA upgrade analysis — prompt

> Repeatable, config-driven before/after analysis of Shaka 6001 on the ZA tenant around the 2026-11-04 app upgrade, with device-model, webview and chart output.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The ZA app upgrade (`v2026.10.27.01` → `v2026.11.03.02`, 2026-11-04 16:30–17:00 IST) needs a before/after view of Shaka 6001: which device models fail, and whether the error comes from an Android
WebView (`wv` token in the user agent). The analysis will be re-run many times (new dates, new cuts), so it is built as thin, config-driven scripts over shared helpers, not one-off queries.

The definitions live in `investigations/shaka-6001/config/analysis.yaml` (tenant ZA, default start 2026-11-01, before/after versions, upgrade window). Before = timestamp earlier than 16:30 IST or
version `v2026.10.27.01`; after = later than 17:00 IST or version `v2026.11.03.02`; inside the window the app version alone decides.

## Scope guard

In bounds: `investigations/shaka-6001/` (scripts, scripts/lib, tests, config, output, docs), a promoted shared user-agent parser under `scripts/lib/`, `SCRIPTS.md`, `CONTEXT.md`. Out of bounds: other
tenants (ZA only), changes to `ctap-smvod` behaviour (its `parse_user_agent` is reused or moved with its tests kept green), `src/lib/charts/` internals (use `render_*` as-is; no new chart type without
a second consumer, per `docs/guides/chart-guidelines.md`). Analysis code only; no runtime service changes.

## Session-start load hints

- `docs/guides/chart-guidelines.md` (chart type table, `write_chart_png`, `ChartError` handling) and `docs/guides/query-catalog.md` before any new Athena SQL.
- `docs/guides/tenant-resolution.md` and `python scripts/resolve_tenant.py ...` before any Athena or Lightstep call.
- `investigations/ctap-smvod/scripts/parse_debug_user_agents.py` (`parse_user_agent`) and `lib/debug_event_parser.py` (eventdata flattening) are the existing code to reuse.
- Local data order: `investigations/shaka-6001/data/athena/ZA/`, `investigations/ctap-smvod/data/athena/ZA/`, `investigations/ctap-smvod/output/ZA/`, `output/ZA/`; only query `ccl_debug_events` for
  dates or fields the local files lack, and save the result under `investigations/shaka-6001/data/athena/ZA/`.

## Task overview

- SU-1 — config loader and before/after classifier.
- SU-2 — shared user-agent parser (model, build, webview) and local-data loader.
- SU-3 — per-event enrichment table (device, webview, period).
- SU-4 — before/after 6001 counts and rates by webview and by device model.
- SU-5 — Chrome/Android version and device-level (drmenabled, mixed webview) cuts.
- SU-6 — charts via `src/lib/charts`.
- SU-7 — one-command runner, docs and registry.
- SU-8 — guest-login redirect (`guestLoginPrompt-redirect`) extract from `fact_navigation_interactions`.
- SU-9 — 6001 users and successful playback (`playback_outcome = DESTROY`).
- SU-10 — daily top 10 households and devices impacted by 6001.
- SU-11 — user tenure (how long since first seen) and stickiness, cross-referenced with success rate.

## Definition of done

Mirrors `tasks.md` "Story done when": one command re-runs every analysis for any ZA date range using the config, each script has tests, outputs and charts land under `output/ZA/`, and docs and
`SCRIPTS.md` list every script.

## Perspectives not covered

Other tenants (GH, ZM); non-Android clients (iOS, desktop user agents are bucketed only); root-causing the 6001 itself; volume normalisation by active devices (rates use events and sessions in the
local data only).
