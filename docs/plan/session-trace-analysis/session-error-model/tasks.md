# Session error model (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: EM-1, EM-2, EM-3, EM-4, EM-5.**

- [ ] **EM-1** — Pure first-error library over flat eventdata, mDRM failures and debug states | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **EM-2** — Cross-day outcome classifier and registered Athena query | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **EM-3** — Cross-check against the error and adoption reports, with the late-ingest reconciliation line | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **EM-4** — Outcome × first-error-code report and charts for all seven outcome classes | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **EM-5** — Docs and CONTEXT.md; unblock PF-8 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **EM-1** — A pure function returns, per session, the first error (code, source, time) and `all_error_codes` from the existing flat eventdata, mDRM failure rows and debug states, following the rule
  in `prompt.md`; tests cover tie-breaking, an mDRM-only session, a debug-only session and a session with no error.
- **EM-2** — A pure classifier assigns the mutually exclusive outcome (success, VSF, EBVS, VPF, VPT, buffering_no_end, startup_no_followup) per session across days with a `crossed_midnight` flag, and
  a catalogued query returns the per-session inputs for a date plus a look-ahead window.
- **EM-3** — For ZA 2026-10-24 the per-session split reproduces the evidence in `prompt.md` within the late-ingest tolerance, and a reconciliation line against the adoption report is printed; the
  first error agrees with the existing error report for 1xxx/6xxx sessions.
- **EM-4** — One command writes, for a tenant and date, a CSV and markdown table of session counts by outcome class and first error code (with `(none)` where no code was observed) and the share of
  sessions in each class that carry any code; it reproduces the ZA 2026-10-24 tables in `prompt.md` within the late-ingest tolerance. It also writes four PNG charts (attempts by outcome, first-error
  source per outcome, mDRM reach per outcome, non-success rate by device attribute; none per error code) to `output/<TENANT>/charts/`, each labelled with the sources included.
- **EM-5** — `usage.md` and `CONTEXT.md` describe the model; PF-8 points at it instead of defining its own rule.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` and add one line to your backlog/session-log file. When the whole story is
done, archive per `docs/plan/README.md`.
