# Monthly error code pipeline — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec. Every deliverable is generated for all four OpCos (ZA, NG, ZM, GH) for the month being analysed (September 2026 first).

**Open: MEC-0, MEC-1, MEC-2, MEC-3, MEC-4, MEC-5, MEC-6, MEC-7, MEC-8, MEC-9, MEC-10, MEC-11, MEC-12, MEC-13, MEC-14, MEC-15.** Exceptions to top-down: MEC-2 depends on MEC-8, so do MEC-8 before
MEC-2; MEC-10 (the guest-login MCP check) needs no CSV and runs first among the guest tasks, before MEC-9, MEC-11 and MEC-12.

- [ ] **MEC-0** — September adoption-session-report CSV for all OpCos, via a month orchestrator over the existing aws_access_cli runner | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-1** — September adoption-report (household counts) CSV for all OpCos, via the same orchestrator | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-2** — September adoption-gap-analysis-session CSV for all OpCos, with the attempts_sum_check column (depends on MEC-8) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-3** — define error-code source and count grain; add the monthly error-code catalog query (pending dedup decision) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  hook | SHA: —
- [ ] **MEC-4** — finalize runbook, usage.md, SCRIPTS.md | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **MEC-5** — verify one playback outcome per session (raw-data check before the adoption CSVs are trusted; run before MEC-2 sign-off) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-6** — join the session and household adoption CSVs into per-day concentration ratios (sessions per household, share of households affected) | Owner: Copilot CLI | Model: claude-sonnet-5.5
  | Review: code-reviewer hook | SHA: —
- [ ] **MEC-7** — top-N households by VSF/EBVS sessions for the month, to name any small group driving the failures | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA:
  —
- [ ] **MEC-8** — VSF-aware playback-outcome template and gap wrapper for this investigation (VSF its own bucket; shared SQL untouched); prerequisite of MEC-2 | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-9** — September guest-session-report CSV for all OpCos, via the month orchestrator with the `_sept26` debug table | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  hook | SHA: —
- [ ] **MEC-10** — guest-login MCP check, run first: on 1-2 households via the Athena MCP, does a guest-login household attempt playback within 24h under a matchable id? Records go or no-go (docs
  only; needs no CSV) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **MEC-11** — daily guest-login funnel rates and day-level co-movement with playback attempts, from the MEC-0, MEC-1 and MEC-9 CSVs (no Athena; depends on those three and follows MEC-10) | Owner:
  Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-12** — guest-login to playback attribution (24h window) per day, built only if MEC-10 recorded a go | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —

- [ ] **MEC-13** — September shaka-error-session CSV (distinct sessions per PLAYER_ERROR code per day) for all OpCos, via the month orchestrator with the `_sept26` debug table; separate from MEC-3 |
  Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —

- [ ] **MEC-14** — reconcile Shaka error sessions (debug table) with `unified_sessions` `PLAYER_ERROR` end reasons per day for all OpCos, classifying debug-only sessions; depends on MEC-13 | Owner:
  Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —

- [ ] **MEC-15** — eventdata shape census per OpCo and error code, then extend the ctap-smvod error-eventdata flattener only for the gaps found | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer hook | SHA: —

## Story done when

- **MEC-0** — `output/<OPCO>/daily/2026-09_adoption-session-report.csv` exists in this investigation for all four OpCos, one row per day 2026-09-01..30 with the four session columns.
- **MEC-1** — `output/<OPCO>/daily/2026-09_adoption-report.csv` exists for all four OpCos, one row per day with the six household columns.
- **MEC-2** — a September `adoption-gap-analysis-session` CSV exists under `output/<OPCO>/daily/` for all four OpCos, with `VOD-Playback-Attempt-Sessions`, the six disjoint outcome columns
  (`Successful-VOD-Playback-Sessions`, `VSF-Sessions`, `EBVS-Sessions`, `playing_no_end_sessions`, `play_stage_error_sessions`, `play_timeout_sessions`) and `attempts_sum_check` (their sum, which must
  equal attempts).
- **MEC-3** — the table, error field and count grain are documented, and a catalog query renders for any OpCo and month.
- **MEC-4** — `usage.md` documents every script and the run order, and `SCRIPTS.md` registers them.
- **MEC-5** — `output/<OPCO>/daily/2026-09_playback-outcome-uniqueness-check.csv` exists for all four OpCos with one row per day; the script exits non-zero if any day has a session in more than one
  playback outcome or the outcome buckets do not sum to attempts.
- **MEC-6** — `output/<OPCO>/daily/2026-09_household-concentration.csv` exists for all four OpCos with one row per day and the ratio columns for attempts, success, VSF and EBVS.
- **MEC-7** — `output/<OPCO>/daily/2026-09_top-vsf-households.csv` exists for all four OpCos with the top-N households and their share of the month's VSF and EBVS sessions.
- **MEC-8** — `queries/athena/mtn-monthly_playback_outcome_vsf.sql` and `scripts/run_gap_session_report.py` exist with tests green; the template classifies each session as success, VSF, EBVS,
  play-stage error, play-timeout or `playing_no_end` (first match wins), and the shared SQL is unchanged.
- **MEC-9** — `output/<OPCO>/daily/2026-09_guest-session-report.csv` exists for all four OpCos, one row per day 2026-09-01..30 with `unique_guest_session`, `guest_login_prompt_hhid`,
  `guest_login_start_hhid` and `guest_login_cancel_hhid`, and `unique_guest_session` was read from `<id>_ccl_debug_events_sept26`, not the default `<id>_ccl_debug_events` table.
- **MEC-10** — the MCP validation result (go or no-go, with the sampled households' evidence) is recorded in `docs/guest-login-attribution-check.md`.
- **MEC-11** — `output/<OPCO>/daily/2026-09_guest-funnel.csv` exists for all four OpCos with one row per day: `guest_start_rate`, `guest_cancel_rate`, the attempt columns and their day-over-day
  changes, plus one monthly correlation row per OpCo; the script fails loudly if an input CSV or day set is missing.
- **MEC-12** — only on a MEC-10 go: `output/<OPCO>/daily/2026-09_guest-login-attribution.csv` exists for all four OpCos with the 24h attribution columns; on a no-go the task closes with that finding.
- **MEC-13** — `output/<OPCO>/daily/2026-09_shaka-error-sessions.csv` exists for all four OpCos, one row per day 2026-09-01..30 with one distinct-session column per error code, read from
  `<id>_ccl_debug_events_sept26`, not the default table; the open checks in `stories.md` (session grain, 2026-09-30, reference vs `_sept26`, VSF relation) are reported, not assumed.
- **MEC-14** — `output/<OPCO>/daily/2026-09_shaka-vs-unified-errors.csv` exists for all four OpCos with one row per day: distinct debug error sessions, distinct unified `PLAYER_ERROR` sessions (split
  by `event_type`), their overlap both ways, and the debug-only sessions split into another end reason vs absent from `unified_sessions`; the same run settles MEC-13 checks (b) and (c).
- **MEC-15** — a coverage table exists in `docs/eventdata-shape-census.md` listing, per OpCo and error code, the `eventdata` key paths present (count, share populated) against the paths
  `flatten_error_eventdata.py` reads; any extension of the flattener covers only gaps in that table, keeps existing columns and outputs unchanged, and has regression tests; the per-code flat output
  appends each day into one file per error code instead of one file per date, deduplicated on `messageid`.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to the backlog/session-log file. When the whole story is
done, archive it per the repo convention — do not leave a done story half-archived.
