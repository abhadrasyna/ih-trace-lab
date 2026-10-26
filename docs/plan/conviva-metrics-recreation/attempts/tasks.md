# Attempts — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: CMR-ATT-4, CMR-ATT-5, CMR-ATT-6, CMR-ATT-7.**

- [x] **CMR-ATT-1** — POC script: per-interval attempts from Athena CREATE events, with reconciliation against session.csv and Lightstep | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: c61dafe
- [x] **CMR-ATT-2** — Chart on the shared theme via the scratch line renderer, 5-minute default bucket | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: eba7b97
- [x] **CMR-ATT-3** — Chart header streamlined: title, KPI under it, metadata footer; chart accepted as final | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 04a6f01
- [ ] **CMR-ATT-4** — Explain the 138-140 CREATE sessions missing from Athena exports and the extra Lightstep sessions | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-ATT-5** — Settle the open definition points: formula, reference number, day boundary, auto-play and revived sessions | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-ATT-6** — Prove the POC generalises: run it for another tenant and another date | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-ATT-7** — Graduate the POC and the line renderer (separate go-ahead) | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —

## Story done when

- **CMR-ATT-1** — The POC runs for ZA and 2026-10-24 and prints the attempts total with reconciliation counts.
- **CMR-ATT-2** — The chart follows `docs/guides/chart-guidelines.md` and its renderer lives in `scratch/_lib/`.
- **CMR-ATT-3** — The chart header is accepted by the user as final.
- **CMR-ATT-4** — Each gap category has a stated cause, backed by sample sessions.
- **CMR-ATT-5** — The definition, day boundary and edge-case rules are written down, with Conviva's reference number if one exists.
- **CMR-ATT-6** — The POC runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.
- **CMR-ATT-7** — Tested `scripts/dev/` and `src/lib/charts/` versions exist and the scratch copies are retired.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
