# Attempts — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Phase 1 (POC, ATT-1 to ATT-3 and ATT-8) is done. Phase 2 (formal recreation of the code and the data) is open: CMR-ATT-5, CMR-ATT-4, CMR-ATT-6, CMR-ATT-9, CMR-ATT-7.**

**Execution order (user, 2026-10-27):** `../concurrent-plays/` is executed first. CMR-ATT-5 (discussion) may run at any time; CMR-ATT-4, CMR-ATT-6 and CMR-ATT-9 wait for CMR-CP-2 (the raw export);
CMR-ATT-7 waits for CMR-CP-6, which builds the shared line renderer, breakdown helper and report writer that ATT-7 reuses.**

- [x] **CMR-ATT-1** — POC script: per-interval attempts from Athena CREATE events, with reconciliation against session.csv and Lightstep | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: c61dafe
- [x] **CMR-ATT-2** — Chart on the shared theme via the scratch line renderer, 5-minute default bucket | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: eba7b97
- [x] **CMR-ATT-3** — Chart header streamlined: title, KPI under it, metadata footer; chart accepted as final | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 04a6f01
- [x] **CMR-ATT-8** — POC markdown report: attempts chart, headline, top-10 content from Athena `session.csv`, unresolved row | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  | SHA: 01d0df6
- [ ] **CMR-ATT-5** — Settle the open definition points: formula, reference number, day boundary, auto-play and revived sessions (discussion, no code; runs first so ATT-4 builds on a settled
  definition) | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-ATT-4** — Formal fetch of the attempts inputs, derived from the POC: CREATE time, content title and household per session, by script with catalogued queries (needs CMR-CP-2 done) | Owner:
  Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-ATT-6** — Prove the POC generalises: run it for another tenant and another date | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-ATT-9** — Close the data gaps for the report: find the source for linear vs VOD and for device type, then add the second chart and the device and playback-type tables (short report format;
  shared join helper)
  | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-ATT-7** — Formal recreation: graduate the POC, the renderer, the report and the data queries into tested production code, reusing and extending existing runners and shared helpers
  (separate go-ahead) | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —

## Story done when

- **CMR-ATT-1** — The POC runs for ZA and 2026-10-24 and prints the attempts total with reconciliation counts.
- **CMR-ATT-2** — The chart follows `docs/guides/chart-guidelines.md` and its renderer lives in `scratch/_lib/`.
- **CMR-ATT-3** — The chart header is accepted by the user as final.
- **CMR-ATT-8** — The report for ZA, 2026-10-24 shows the chart and a top-10 content table that reconciles to the attempts total, from Athena only.
- **CMR-ATT-4** — A tested runner fetches the CREATE times and the title and household per session for any tenant and date from catalogued Athena queries; the POC's inputs are all covered.
- **CMR-ATT-5** — The definition, day boundary and edge-case rules are written down, with Conviva's reference number if one exists, and one source is chosen between the CREATE rule and
  `chart_playback_attempts.py`.
- **CMR-ATT-6** — The POC runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.
- **CMR-ATT-9** — Linear and VOD attempts are separated in a second chart and the device and playback-type tables are in the report in the short format, or the missing source is documented as a
  blocker.
- **CMR-ATT-7** — The attempts script in `investigations/conviva-metrics/scripts/` exists with tests and reuses the `src/lib/` renderer, breakdown helper and report writer built in CMR-CP-6, the
  report and its Athena queries are in the catalog and run for any tenant and date, the report reads the saved exports, and the scratch copies are retired.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
