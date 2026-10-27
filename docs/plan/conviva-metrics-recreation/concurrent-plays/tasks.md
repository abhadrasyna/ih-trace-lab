# Concurrent Plays — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**The POC (commit `1bcb06e`) is evidence, not a task. All tasks below are the formal build.**

**Execution order:** this story is executed before `../attempts/` (CMR-CP-2 gives attempts its raw export; CMR-CP-6 builds the renderer, breakdown helper and report writer attempts reuses).

- [x] **CMR-CP-1** — Settle the definition points and decide the report content with the user | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-CP-2** — Build the formal full-day raw debug-events download (catalogued query, tested runner, shared `day_bounds`, reuse or extend the existing flatten helpers) | Owner: Copilot CLI |
  Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CP-3** — Explain the differences: open playing intervals, sessions outside `session.csv`, playing versus alive | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CP-4** — Prove the POC generalises: run it for another tenant and another date | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CP-5** — Close the data gaps: device type and linear versus VOD, then extend the report | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CP-6** — Formal recreation: graduate the POC, the renderer, the report and the data queries into tested production code (separate go-ahead) | Owner: Copilot CLI | Model: n/a | Review:
  code-reviewer | SHA: —

## Story done when

- **CMR-CP-1** — The end rule for open intervals, the closing events, the day boundary and the report sections are written down, with Conviva's reference number if one exists.
- **CMR-CP-2** — A catalog query, a tested `run_athena_debug_events_raw.py` runner and a saved raw export (`eventdata` untouched) exist for ZA, 2026-10-24, the flat step reuses the existing helpers,
  and the POC rebuilt from the raw export still gives 16.
- **CMR-CP-3** — Each difference has a stated cause backed by sample sessions, and the report says whether it belongs in the Conviva definition.
- **CMR-CP-4** — The POC runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.
- **CMR-CP-5** — Device and linear/VOD splits are in the report, or the missing source is documented as a blocker.
- **CMR-CP-6** — Tested `investigations/conviva-metrics/scripts/` and `src/lib/` (charts, breakdown, report) versions exist, the report and its queries are in the catalog and run for any tenant and
  date, and the scratch copies are retired.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
