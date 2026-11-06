# Shaka 6001 ZA upgrade analysis — prompt

> Repeatable, config-driven before/after analysis of Shaka 6001 on the ZA tenant around the 2026-11-04 app upgrade, with device-model, webview, recovery, guest-login and tenure views, and charts.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) and `spec.md` (audit evidence) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The ZA app upgrade (`v2026.10.27.01` → `v2026.11.03.02`, 2026-11-04 16:30–17:00 IST) needs a before/after view of Shaka 6001: which device models fail, whether the error comes from an Android WebView
(`wv` token in the user agent), whether affected users later play successfully, how many guests are pushed out to a browser to log in, and how long active users have been around. The analyses will be
re-run many times (new dates, new cuts), so they are thin, config-driven scripts over shared helpers, not one-off queries. `spec.md` holds the audit of what already exists.

The definitions live in `investigations/shaka-6001/config/analysis.yaml` (tenant ZA, default start 2026-11-01, before/after versions, upgrade window). Before = timestamp earlier than 16:30 IST or
version `v2026.10.27.01`; after = later than 17:00 IST or version `v2026.11.03.02`; inside the window the app version alone decides. Table timestamps are UTC and are converted to IST first.

## Scope guard

In bounds:
- `investigations/shaka-6001/` (scripts, scripts/lib, tests, config, docs, `data/`, `output/<TENANT>/`).
- Shared code promoted into `src/lib/` (user-agent parser, playback-success rule, ranking) with thin re-exports left in `ctap-smvod` so its tests stay green.
- `SCRIPTS.md`, `queries/athena/` and `CONTEXT.md`.

Out of bounds:
- Tenants other than ZA.
- `ctap-smvod` behaviour changes.
- `src/lib/charts/` internals (use `render_*` as-is; no new chart type without a second consumer, per `docs/guides/chart-guidelines.md`).
- Runtime services.
- Installing the crontab (a human step; the story delivers the entry point and the documented line).

This story is analysis code only.

## Session-start load hints

- `spec.md` (audit and reuse table), `docs/guides/chart-guidelines.md`, `docs/guides/query-catalog.md` before any new Athena SQL, and `docs/guides/functional-code-taxonomy.md` before adding to
  `src/lib/`.
- `docs/guides/tenant-resolution.md` and `python scripts/resolve_tenant.py --system athena --tenant ZA` before any Athena call; use `src.lib.athena.AthenaClient` and `src.lib.paths.YamlPathResolver`.
- Local data order: `investigations/shaka-6001/data/athena/ZA/`, `investigations/ctap-smvod/data/athena/ZA/`, `investigations/ctap-smvod/output/ZA/`, `output/ZA/`; only query for dates or fields the
  local files lack, and save the result under `investigations/shaka-6001/data/athena/ZA/`.

## Task overview

- SU-1 — config loader and before/after classifier.
- SU-2 — shared libs in `src/lib/`: user-agent parser, playback-success rule, ranking.
- SU-3 — local-data loader and Athena fetch wrapper (injected client).
- SU-4 — per-event enrichment table (device, webview, period).
- SU-5 — before/after 6001 counts by webview and device model.
- SU-6 — Chrome/Android version and device-level cuts.
- SU-7 — charts for SU-5 and SU-6.
- SU-8 — guest-login redirect (`guestLoginPrompt-redirect`) fetch.
- SU-9 — guest-login redirect analysis (debug-table join, before/after).
- SU-10 — 6001 cohort and playback-outcome data prep.
- SU-11 — 6001 recovery analysis (successful playback after 6001).
- SU-12 — daily top 10 households and devices impacted by 6001.
- SU-13 — daily top 10 device models impacted by 6001.
- SU-14 — user tenure and stickiness vs success rate.
- SU-15 — step-registry runner, daily cron mode, docs and registry.

## Definition of done

Mirrors `tasks.md` "Story done when": one command re-runs every analysis for any ZA date range using the config, each script has offline tests, outputs and charts land under
`investigations/shaka-6001/output/ZA/`, and docs and `SCRIPTS.md` list every script.

## Perspectives not covered

Other tenants (GH, ZM); non-Android clients (iOS and desktop user agents are bucketed only); root-causing the 6001 itself; normalising by all active devices (rates use events and sessions in the
available data); a real subscription date (tenure is a first-seen proxy); architecture diagrams (skipped by decision, 2026-11-06).
