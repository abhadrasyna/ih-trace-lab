# Monthly error code pipeline — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec. Every deliverable is generated for all four OpCos (ZA, NG, ZM, GH) for the month being analysed (September 2026 first). IDs ascend in run order; `id-renumber-map.json` records the old-to-new
mapping from the 2026-10-11 renumber.

**Phases (run in this order):** A Foundations (MEC-0 to MEC-2) → B Data fetch, so all data is local before any analysis (MEC-3 to MEC-13) → C Validation and reconciliation (MEC-14 to MEC-18) → D
Analysis on local data (MEC-19 to MEC-27) → E Synthesis and close-out (MEC-28, MEC-29).

**Open: MEC-0 to MEC-29** (all 30 tasks). Notes on order: MEC-3 (guest-login MCP check, docs only, needs no CSV) runs first among the guest tasks, so MEC-9 only runs on a go; MEC-8 depends on MEC-0
and is signed off only after MEC-14 passes; MEC-27 stays blocked until the user supplies the MTN business error list; MEC-12 is optional.

## A. Foundations (code and definitions, no data pulled)

- [ ] **MEC-0** — VSF-aware playback-outcome template and gap wrapper for this investigation (VSF its own bucket; shared SQL untouched); prerequisite of MEC-8; also settles the bucket name
  (`playing_no_end_sessions`, not the ZA sample's `incomplete_no_destroy_sessions`) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-1** — statistics helpers (Wilson interval, p-prime control limits, concentration, agreement, day-of-week split) used by MEC-19, MEC-20, MEC-15 and MEC-22 | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-2** — define error-code source and count grain; add the monthly error-code catalog query (pending dedup decision) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  hook | SHA: —

## B. Data fetch (Athena or MCP into local files; nothing is analysed here)

- [ ] **MEC-3** — guest-login MCP check, run first among the guest tasks: on 1-2 households via the Athena MCP, does a guest-login household attempt playback within 24h under a matchable id? Records
  go or no-go (docs only; needs no CSV) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **MEC-4** — September adoption-session-report CSV for all OpCos, via a month orchestrator over the existing aws_access_cli runner | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-5** — September adoption-report (household counts) CSV for all OpCos, via the same orchestrator | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-6** — September guest-session-report CSV for all OpCos, via the month orchestrator with the `_sept26` debug table | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  hook | SHA: —
- [ ] **MEC-7** — September shaka-error-session CSV (distinct sessions per PLAYER_ERROR code per day) for all OpCos, via the month orchestrator with the `_sept26` debug table; separate from MEC-2 |
  Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-8** — September adoption-gap-analysis-session CSV for all OpCos, with the attempts_sum_check column (depends on MEC-0; sign-off waits for MEC-14) | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-9** — guest-login to playback attribution (24h window) per day, built only if MEC-3 recorded a go | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-10** — startup time, High Startup Time and EBVS abandonment per day for all OpCos, split by end reason; depends on MEC-0 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-11** — plays with no end record and the mid-month shift to timeouts, per OpCo | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-12** — approximate Rebuffering Ratio (optional; only if the story needs a quality-of-playback beat beyond outcomes) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  hook | SHA: —
- [ ] **MEC-13** — eventdata shape census per OpCo and error code, then extend the ctap-smvod error-eventdata flattener only for the gaps found | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer hook | SHA: —

## C. Validation and reconciliation (is the fetched data trustworthy?)

- [ ] **MEC-14** — verify one playback outcome per session (raw-data check before the adoption CSVs are trusted; run before MEC-8 sign-off) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-15** — reconcile Shaka error sessions (debug table) with `unified_sessions` `PLAYER_ERROR` end reasons per day for all OpCos, classifying debug-only sessions; depends on MEC-7 | Owner:
  Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-16** — find where absent debug error sessions are: unwindowed `unified_sessions` lookup and same-device check (docs only) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none |
  SHA: —
- [ ] **MEC-17** — classify every debug PLAYER_ERROR session against `unified_sessions` (VSF, VPF-like, other end reason, absent) for all of September and all OpCos, with the error-minus-session-end
  timing test; depends on MEC-15 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-18** — check the class-2 VPF-proxy against Conviva's conditions (error after first frame, error-to-end within 150 s); depends on MEC-17 | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer hook | SHA: —

## D. Analysis (local data only; no new Athena queries)

- [ ] **MEC-19** — join the session and household adoption CSVs into per-day concentration ratios (sessions per household, share of households affected) | Owner: Copilot CLI | Model: claude-sonnet-5.5
  | Review: code-reviewer hook | SHA: —
- [ ] **MEC-20** — top-N households by VSF/EBVS sessions for the month, to name any small group driving the failures | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA:
  —
- [ ] **MEC-21** — daily guest-login funnel rates and day-level co-movement with playback attempts, from the MEC-4, MEC-5 and MEC-6 CSVs (no Athena; follows MEC-3) | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-22** — Conviva comparison table per OpCo (our definitions vs Conviva-aligned: attempts, plays, VSF, EBVS, ended plays, VPF-proxy, residual); depends on MEC-0, MEC-14 and MEC-1 | Owner:
  Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-23** — business vs technical evidence profile for every error code in the flattened GH eventdata, one code at a time (3016 and 1003 profiled; feeds MEC-27, which stays blocked on the MTN
  business list) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none (docs only) | SHA: —
- [ ] **MEC-24** — analyse the four Astro Pulse exports (`data/reference/AstroErrorCode/`: VSF-B, VSF-T, VPF-B, VPF-T) as a reference for MEC-27 (docs plus one small parser script) | Owner: Copilot
  CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-25** — device analysis per error code from `user_agent` (model, Android version and build for Android; OS and browser version for iOS, macOS, Windows), with the `is_wv` split | Owner:
  Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-26** — `is_wv` analysis per error code on South Africa data (the GH sample has no WebView events) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none (docs only) | SHA: —
- [ ] **MEC-27** — business vs technical per-code mapping file and the rates split (per 100 attempts for start errors, per 100 ended plays for play-stage errors); blocked until the user supplies the
  MTN Business Error Configuration list | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —

## E. Synthesis and close-out

- [ ] **MEC-28** — cross-OpCo playback-state report for September 2026 (ZA, NG, ZM, GH): outcome mix, trend, error codes, concentration, device and WebView, app version and day-of-week cuts, told per
  `docs/analysis-storytelling-framework.md`; depends on MEC-1, 4, 7, 8, 10, 11, 14, 15, 17, 19, 20, 22, 25 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none (docs only) | SHA: —
- [ ] **MEC-29** — finalize runbook, usage.md, SCRIPTS.md | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

### A. Foundations

- **MEC-0** — `queries/athena/mtn-monthly_playback_outcome_vsf.sql` and `scripts/run_gap_session_report.py` exist with tests green; the template classifies each session as success, VSF, EBVS,
  play-stage error, play-timeout or `playing_no_end` (first match wins), and the shared SQL is unchanged.
- **MEC-1** — the statistics helpers module exists with one happy-path and one edge-case test per helper, no network.
- **MEC-2** — the table, error field and count grain are documented, and a catalog query renders for any OpCo and month.

### B. Data fetch

- **MEC-3** — the MCP validation result (go or no-go, with the sampled households' evidence) is recorded in `docs/guest-login-attribution-check.md`.
- **MEC-4** — `output/<OPCO>/daily/2026-09_adoption-session-report.csv` exists in this investigation for all four OpCos, one row per day 2026-09-01..30 with the four session columns.
- **MEC-5** — `output/<OPCO>/daily/2026-09_adoption-report.csv` exists for all four OpCos, one row per day with the six household columns.
- **MEC-6** — `output/<OPCO>/daily/2026-09_guest-session-report.csv` exists for all four OpCos, one row per day 2026-09-01..30 with `unique_guest_session`, `guest_login_prompt_hhid`,
  `guest_login_start_hhid` and `guest_login_cancel_hhid`, and `unique_guest_session` was read from `<id>_ccl_debug_events_sept26`, not the default `<id>_ccl_debug_events` table.
- **MEC-7** — `output/<OPCO>/daily/2026-09_shaka-error-sessions.csv` exists for all four OpCos, one row per day 2026-09-01..30 with one distinct-session column per error code, read from
  `<id>_ccl_debug_events_sept26`, not the default table; the open checks in `stories.md` (session grain, 2026-09-30, reference vs `_sept26`, VSF relation) are reported, not assumed.
- **MEC-8** — a September `adoption-gap-analysis-session` CSV exists under `output/<OPCO>/daily/` for all four OpCos, with `VOD-Playback-Attempt-Sessions`, the six disjoint outcome columns
  (`Successful-VOD-Playback-Sessions`, `VSF-Sessions`, `EBVS-Sessions`, `playing_no_end_sessions`, `play_stage_error_sessions`, `play_timeout_sessions`) and `attempts_sum_check` (their sum, which must
  equal attempts).
- **MEC-9** — only on a MEC-3 go: `output/<OPCO>/daily/2026-09_guest-login-attribution.csv` exists for all four OpCos with the 24h attribution columns; on a no-go the task closes with that finding.
- **MEC-10** — a per-day startup-time CSV exists for all four OpCos (count, average, median, p90, over-10 s and over-8 s, split by end reason), after checking the duration equals
  attempt-to-first-frame.
- **MEC-11** — per OpCo, the plays with no end record and the day the shift to timeouts begins are reported as measured (see `stories.md` MEC-11).
- **MEC-12** — only if built: an approximate Rebuffering Ratio per OpCo-day, labelled approximate.
- **MEC-13** — a coverage table exists in `docs/eventdata-shape-census.md` listing, per OpCo and error code, the `eventdata` key paths present (count, share populated) against the paths
  `flatten_error_eventdata.py` reads; any extension of the flattener covers only gaps in that table, keeps existing columns and outputs unchanged, and has regression tests; the per-code flat output
  appends each day into one file per error code instead of one file per date, deduplicated on `messageid`.

### C. Validation and reconciliation

- **MEC-14** — `output/<OPCO>/daily/2026-09_playback-outcome-uniqueness-check.csv` exists for all four OpCos with one row per day; the script exits non-zero if any day has a session in more than one
  playback outcome or the outcome buckets do not sum to attempts.
- **MEC-15** — `output/<OPCO>/daily/2026-09_shaka-vs-unified-errors.csv` exists for all four OpCos with one row per day: distinct debug error sessions, distinct unified `PLAYER_ERROR` sessions (split
  by `event_type`), their overlap both ways, and the debug-only sessions split into another end reason vs absent from `unified_sessions`; the same run settles MEC-7 checks (b) and (c).
- **MEC-16** — the cause of each absent debug error session is recorded in `docs/` from an unwindowed lookup, reported as measured, not assumed.
- **MEC-17** — `output/<OPCO>/daily/2026-09_error-session-classes.csv` exists for all four OpCos with one row per day and class: sessions, households, error-minus-session-end seconds and error codes
  (counts only).
- **MEC-18** — per OpCo-day, class-2 sessions with the error after `PLAY` start and error-to-end within 150 s are counted and labelled VPF-proxy, never VPF.

### D. Analysis

- **MEC-19** — `output/<OPCO>/daily/2026-09_household-concentration.csv` exists for all four OpCos with one row per day and the ratio columns for attempts, success, VSF and EBVS.
- **MEC-20** — `output/<OPCO>/daily/2026-09_top-vsf-households.csv` exists for all four OpCos with the top-N households and their share of the month's VSF and EBVS sessions.
- **MEC-21** — `output/<OPCO>/daily/2026-09_guest-funnel.csv` exists for all four OpCos with one row per day: `guest_start_rate`, `guest_cancel_rate`, the attempt columns and their day-over-day
  changes, plus one monthly correlation row per OpCo; the script fails loudly if an input CSV or day set is missing.
- **MEC-22** — `output/<OPCO>/2026-09_conviva-comparison.csv` exists for all four OpCos, one row per metric with our value, the Conviva-aligned value and whether it changes.
- **MEC-23** — `docs/error-code-classification-evidence.md` has one section per error code (every code in the story's coverage list in `stories.md` MEC-23, ticked as done) with the evidence profile,
  the candidate class (business / technical / undecided), confidence and what would settle it; counts only, labelled a proposal from text and signals, not Conviva's classification.
- **MEC-24** — `docs/astro-business-technical-reference.md` records, from the four Astro exports, per error key: class (VSF-B, VSF-T, VPF-B, VPF-T), impacted attempts or ended plays and share, keys
  present in both classes (for example 6008), and the export format to request for MTN; counts only, labelled a reference from another account, not an MTN classification.
- **MEC-25** — per error code, a device table from `user_agent` (Android model, version, build; OS family and browser version otherwise) with the `is_wv` split and the unparsed share stated; no ids.
- **MEC-26** — per error code on South Africa data, the `is_wv` share and wv vs non-wv outcomes, stating the source files and dates; the GH sample (all `is_wv` false) is recorded as no evidence.
- **MEC-27** — the per-code business/technical mapping file and the rates split exist (per 100 attempts for start errors, per 100 ended plays for play-stage errors); unmapped codes fail loudly.

### E. Synthesis and close-out

- **MEC-28** — `docs/2026-09-playback-state-all-opcos.md` exists: one-sentence big idea, per-OpCo outcome mix with rates naming their denominators and Wilson intervals, daily trend with control-limit
  outliers, top error codes, household concentration, device/WebView, app-version and day-of-week cuts, limits stated (counts only, no ids); any OpCo or dimension without data is named, not omitted.
- **MEC-29** — `usage.md` documents every script and the run order, and `SCRIPTS.md` registers them.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to the backlog/session-log file. When the whole story is
done, archive it per the repo convention — do not leave a done story half-archived.
