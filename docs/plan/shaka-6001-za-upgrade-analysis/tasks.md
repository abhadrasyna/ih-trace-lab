# Shaka 6001 ZA upgrade analysis — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: SU-1, SU-2, SU-3, SU-4, SU-5, SU-6, SU-7, SU-8, SU-9, SU-10, SU-11, SU-12.**

- [ ] **SU-1** — config loader and before/after classifier | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-2** — shared user-agent parser and local-data loader | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-3** — per-event enrichment table | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-4** — before/after counts by webview and device model | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-5** — Chrome/Android version and device-level cuts | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-6** — charts via shared chart layer | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-7** — one-command runner, docs and registry | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **SU-8** — guest-login redirect extract (`guestLoginPrompt-redirect`) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-9** — 6001 users: did they have a successful playback session | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-10** — daily top 10 households/devices hit by 6001 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-11** — user tenure (first seen) and stickiness vs success rate | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SU-12** — daily top 10 device models hit by 6001 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —

## Story done when

- **SU-1** — classifier returns before/after/unknown for any timestamp and version, window decided by version only, and tests pass.
- **SU-2** — `P11 Build/TP1A.220624.014; wv` style user agents parse to model, build, Android, Chrome and webview; local files load by date range with a gap report.
- **SU-3** — one enriched CSV per date range under `output/ZA/`, with unparsed user agents counted, not dropped.
- **SU-4** — before/after 6001 counts and rates split by webview and by model, written as CSV.
- **SU-5** — Chrome/Android version and drmenabled/mixed-webview device tables written as CSV.
- **SU-6** — PNG charts for SU-4/SU-5 under `output/ZA/charts/`; a chart failure never blocks CSVs.
- **SU-7** — a single command re-runs everything for `--start-date/--end-date`; `SCRIPTS.md`, `docs/usage.md` and `CONTEXT.md` updated.
- **SU-8** — a script fetches `guestLoginPrompt-redirect` navigation rows per date, saves them locally, and reports daily and before/after counts; SU-7's runner includes it.
- **SU-9** — per 6001 device/household: first 6001 time, whether a `DESTROY` playback session exists before/after it, and the share recovering, split by period and webview.
- **SU-10** — one ranked top-10 table per day (households and devices) with 6001 counts, model, webview flag and period, plus a trend chart; ties and guests handled as specified.
- **SU-11** — active households bucketed by tenure with success rate (and 6001 rate) per bucket, tenure limits stated, and a chart; ready for the Sunday meeting.
- **SU-12** — one ranked top-10 device-model table per day with events, devices and rate, plus a chart; shares its day basis and parser with SU-10.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `CONTEXT.md` and add one line to the session log. When the whole story is done, archive it with
`python scripts/dev/archive_completed_story.py shaka-6001-za-upgrade-analysis`.
