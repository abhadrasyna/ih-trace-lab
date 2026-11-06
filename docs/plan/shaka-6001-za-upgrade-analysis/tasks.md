# Shaka 6001 ZA upgrade analysis — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec and `spec.md` for the audit of existing code.

**Open: none — story complete.**

- [x] **SU-1** — config loader and before/after classifier | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: a7caa70
- [x] **SU-2** — shared libs in src/lib (user agent, playback success, ranking) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 12a7ec8
- [x] **SU-3** — local-data loader and Athena fetch wrapper | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: c47d0ef
- [x] **SU-4** — per-event enrichment table | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 8f6af21
- [x] **SU-5** — before/after counts by webview and device model | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: b95454e
- [x] **SU-6** — Chrome/Android version and device-level cuts | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 8aa8b12
- [x] **SU-7** — charts for SU-5 and SU-6 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 4a074f7
- [x] **SU-8** — guest-login redirect fetch | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 05de623
- [x] **SU-9** — guest-login redirect analysis | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 8accfde
- [x] **SU-10** — 6001 cohort and playback-outcome data prep | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 0640fd0
- [x] **SU-11** — 6001 recovery analysis | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: e5e2ebe
- [x] **SU-12** — daily top 10 households and devices hit by 6001 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 42623fb
- [x] **SU-13** — daily top 10 device models hit by 6001 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 4713665
- [x] **SU-14** — user tenure and stickiness vs success rate | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 96b3c39
- [x] **SU-15** — step-registry runner, daily cron mode, docs and registry | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: 4334ced

## Story done when

- **SU-1** — classifier returns before/after/unknown for any UTC timestamp and version, the window is decided by version only, and tests pass.
- **SU-2** — parser, success rule and ranking live in `src/lib/`, `ctap-smvod` re-exports them, and the P11 `wv` user agent parses correctly.
- **SU-3** — local files load by date range with a gap report, and missing dates are fetched through an injected `AthenaClient` and saved locally.
- **SU-4** — one enriched CSV per date range, with unparsed user agents counted, not dropped.
- **SU-5** — before/after 6001 counts and rates by webview and by model, written as CSV.
- **SU-6** — Chrome/Android version and drmenabled/mixed-webview device tables written as CSV.
- **SU-7** — PNG charts for SU-5 and SU-6; a chart failure never blocks CSVs.
- **SU-8** — redirect rows and their debug-table events are fetched per date and saved locally.
- **SU-9** — daily and before/after redirect counts, journey shape and pre-redirect events reported.
- **SU-10** — the 6001 cohort and per-date playback outcomes are available locally.
- **SU-11** — per-user recovery and recovery rates by period, webview and model, with guests separate.
- **SU-12** — one ranked top-10 table per day for households and devices, plus a trend chart.
- **SU-13** — one ranked top-10 model table per day with rates, plus charts.
- **SU-14** — active households bucketed by tenure with success rate, stated limits, and a chart.
- **SU-15** — one command re-runs everything for `--start-date/--end-date`, a cron-safe daily mode backfills missing dates with a lock, log and FAILED marker; `SCRIPTS.md`, `docs/usage.md` and
  `CONTEXT.md` updated.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `CONTEXT.md` and add one line to the session log. When the whole story is done, archive it with
`python scripts/dev/archive_completed_story.py shaka-6001-za-upgrade-analysis`.
