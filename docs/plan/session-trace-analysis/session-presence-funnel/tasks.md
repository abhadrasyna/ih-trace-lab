# Session presence funnel (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: PF-7a, PF-1, PF-2, PF-6, PF-7b, PF-3, PF-8, PF-4, PF-5.** Depends on `session-error-model/` (EM-1, EM-2) before PF-8.

- [ ] **PF-7a** — Premise check: which sessions are expected in Athena (docs only, no code) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **PF-1** — Pure library: setup-attempt/failed-setup stage first, then three-source session-id sets, funnel stages, buckets, overlaps, per-`session_type` split | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **PF-2** — Report script: dated markdown + CSV for one tenant and date, with the setup-failure, not-observed and athena-only lists | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **PF-6** — Daily debug-not-unified report split by contentId missing/present, with the sessionId list and trend columns | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **PF-7b** — Lightstep forensics of sessions not observed in Athena: lifecycle query, manual review, household concentration, mDRM cross-check | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer | SHA: —
- [ ] **PF-3** — Characterize the sessions not observed in Athena (device, OS, hour, DRM activity; first error once PF-8 exists) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  | SHA: —
- [ ] **PF-8** — Per-session trace matrix CSV and funnel/overlap charts across Lightstep, mDRM, debug and unified, with first error and outcome from `session-error-model` | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **PF-4** — Daily operation: `run_pipeline.py` step and a trend CSV | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **PF-5** — Validate on ZA 2026-10-24, extrapolate to another date and tenant, update docs and CONTEXT.md; run last | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **PF-1** — Pure functions (no file or network I/O) return the setup stage (attempts = sessions created + failed setups) and stage counts, buckets (`present_in_both`, `debug_not_unified`,
  `unified_not_debug`, `not_observed_in_athena`) and overlaps from three id sets; the file-level reads and set diffs reuse `compare_lightstep_athena_sessions.py` and
  `build_session_comparison_daily.py`; tests cover duplicates, blank ids, failed setups by status code and the VOD/linear split.
- **PF-2** — `analyze_session_presence.py --tenant <T> --date <D>` writes a dated markdown report and CSV, a CSV of failed setups (blank `sessionId`, by `http.status_code`), a CSV of sessions not
  observed in Athena and a CSV of sessions in Athena but not in the Lightstep export (`athena_only`, with first-event hour and whether it lies within 2 minutes before an export part boundary).
- **PF-3** — The report breaks the unobserved sessions down by at least device class, OS, browser and hour, split by device-level versus session-level, with a control comparison; first error code is
  added once PF-8 exists.
- **PF-4** — `run_pipeline.py` runs the report as a step (with a skip flag) and a trend CSV gains one row per tenant and date without duplicating re-runs; each row records the export time
  (`max_ingest_timestamp`) so later restatements are visible.
- **PF-5** — The ZA 2026-10-24 run reproduces the baseline in `prompt.md` within its stated tolerance; one other date and one other tenant run clean; open questions are answered; `usage.md` and
  `CONTEXT.md` are current.
- **PF-6** — For any tenant and date, one report lists the sessions in debug states but not `unified_sessions`, split by contentId missing/present with a sessionId CSV, and the trend file carries the
  daily counts.
- **PF-7a** — The findings doc states which sessions are expected in Athena (and the size of that population) before any cause is discussed.
- **PF-7b** — A catalogued Lightstep query and a dated findings doc classify every session in Lightstep but not observed in either Athena table by lifecycle outcome and show whether a few households
  account for them; the ZA 2026-10-24 findings are recorded.
- **PF-8** — For any tenant and date, one CSV has a row per Lightstep session with presence flags for every source, the DRM license status, and the first error (from `session-error-model`) and
  outcome, plus a pattern-count CSV and PNG charts that reproduce the ZA 2026-10-24 numbers.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` and add one line to your backlog/session-log file. When the whole story is
done, archive per `docs/plan/README.md`.
