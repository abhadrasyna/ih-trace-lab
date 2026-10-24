# Daily 3016 sub-category report (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: SUB-3, SUB-4, SUB-5.**

- [x] **SUB-1** — rules module mapping a flat error row to one of 5 sub-categories + priority | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: f2fc20c
- [x] **SUB-2** — events builder: join setupsession/position by sessionId, add parsed browser/model and raw user_agent | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA:
  352a41c
- [ ] **SUB-3** — summary builder: events and distinct households per OpCo and sub-category | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SUB-4** — daily CLI: write both CSVs per OpCo/day and reconcile with the flat-file row counts | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SUB-5** — usage doc, SCRIPTS.md and CONTEXT.md entries; retire the scratch POC | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **SUB-1** — every 3014/3015/3016 row maps to exactly one sub-category; unmatched rows go to "Uncategorised", never dropped; tests are green.
- **SUB-2** — events CSV has one row per error, includes the raw `user_agent`, and rows with an empty `sessionId` or `householdId` never join or count as a shared key.
- **SUB-3** — summary CSV matches the sample format (`date,opco,subcategory,events,households,sessions,priority`) and its event total equals the events CSV row count.
- **SUB-4** — one command produces both CSVs for an OpCo/day and fails loudly when an input file is missing or counts do not reconcile.
- **SUB-5** — the usage doc, `SCRIPTS.md` and `CONTEXT.md` list the new script; the scratch POC is removed or marked superseded.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then add one line to your backlog/session-log file. When the whole story is done, archive it with `python
scripts/dev/archive_completed_story.py ctap-smvod-3016-subcategory-report`.
