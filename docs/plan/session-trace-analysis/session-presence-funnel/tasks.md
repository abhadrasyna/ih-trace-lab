# Session presence funnel (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: PF-1, PF-2, PF-3, PF-4, PF-5, PF-6, PF-7, PF-8.**

- [ ] **PF-1** — Pure library: setup-attempt/failed-setup stage first, then per-source session-id sets, funnel stages, overlaps, per-`session_type` split | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **PF-2** — Report script: dated markdown + CSV for one tenant and date, with the setup-failure and missing-sessions lists | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  | SHA: —
- [ ] **PF-3** — Characterize the sessions missing downstream (device, OS, error codes, DRM activity) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **PF-4** — Daily operation: `run_pipeline.py` step and a trend CSV | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **PF-5** — Validate on ZA 2026-10-24, extrapolate to another date and tenant, update docs and CONTEXT.md | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **PF-6** — Daily debug-not-unified report split by contentId missing/present, with the sessionId list and trend columns | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **PF-7** — Lightstep forensics of sessions missing from both Athena tables: lifecycle query, manual review, household concentration | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none
  | SHA: —
- [ ] **PF-8** — Per-session trace matrix CSV and funnel/overlap charts across Lightstep, mDRM, debug and unified, with a first-error sessionId list | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer | SHA: —

## Story done when

- **PF-1** — Pure functions (no file or network I/O) return the setup stage (attempts = sessions created + failed setups) and stage counts and overlaps from id sets; tests cover duplicates, blank ids,
  failed setups by status code and the VOD/linear split.
- **PF-2** — `analyze_session_presence.py --tenant <T> --date <D>` writes a dated markdown report and CSV, a CSV of failed setups (blank `sessionId`, by `http.status_code`) and a CSV of sessions
  missing downstream.
- **PF-3** — The report breaks the missing sessions down by at least device class, OS and first error code, using existing local files only.
- **PF-4** — `run_pipeline.py` runs the report as a step (with a skip flag) and a trend CSV gains one row per tenant and date without duplicating re-runs.
- **PF-5** — The ZA 2026-10-24 run reproduces the baseline in `prompt.md`; one other date and one other tenant run clean; open questions are answered; `usage.md` and `CONTEXT.md` are current.
- **PF-6** — For any tenant and date, one report lists the sessions in debug states but not `unified_sessions`, split by contentId missing/present with a sessionId CSV, and the trend file carries the
  daily counts.
- **PF-7** — A catalogued Lightstep query and a dated findings doc classify every session in Lightstep but in neither Athena table by lifecycle outcome and show whether a few households account for
  them; the ZA 2026-10-24 findings are recorded.
- **PF-8** — For any tenant and date, one CSV has a row per Lightstep session with presence flags for every source, the DRM license status and the first error with its source, plus a pattern-count CSV
  and PNG charts that reproduce the ZA 2026-10-24 numbers; the first-error rule is documented.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` and add one line to your backlog/session-log file. When the whole story is
done, archive per `docs/plan/README.md`.
