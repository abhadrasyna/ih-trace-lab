# Household usage tracking — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: UT-1, UT-2, UT-3, UT-4, UT-5, UT-6, UT-7.**

- [ ] **UT-1** — Prior-art audit and design review: resolve the report-date/Lightstep-source and Athena-factory decisions, module map, Protocols, planned diagram (docs only) | Owner: Copilot CLI |
  Model: claude-sonnet-5.5 | Review: user approval of the design | SHA: —
- [ ] **UT-2** — Roster file `config/tracked_households.yaml` and a validating loader with the `track` flag | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: tests green + code-reviewer | SHA:
  —
- [ ] **UT-3** — Athena source: query files and a fetcher for sessions, all devices per household, and error detail | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: tests green +
  code-reviewer | SHA: —
- [ ] **UT-4** — Lightstep source: request counts and trace ids per device, from the local export (default) or live (`--live-lightstep`) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: tests
  green + code-reviewer | SHA: —
- [ ] **UT-5** — Pure merge and rule functions: per-person metrics, flags, new-device detection, 7-day trend | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: tests green + code-reviewer |
  SHA: —
- [ ] **UT-6** — Markdown report renderer to the agreed format | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: tests green (golden file) + code-reviewer | SHA: —
- [ ] **UT-7** — CLI entry point, failure handling, README with the cron line, `SCRIPTS.md`, `CONTEXT.md`, final architecture diagram | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: tests
  green + code-reviewer + one real run read by the user | SHA: —

## Story done when

- **UT-1** — the two open decisions are recorded with reasons, the module map and Protocols are approved, and the planned diagram is committed.
- **UT-2** — editing only the YAML adds a person or household; a duplicate device id, an unknown tenant or a malformed entry fails loudly; `track: false` households are skipped.
- **UT-3** — for a date and a roster the fetcher returns sessions with content names, every device seen on each tracked household, and error detail for errored sessions only, all with injected fakes
  in tests.
- **UT-4** — per-device request counts and trace ids are returned from the local export, or live with the flag, with no network in tests.
- **UT-5** — every flag is a separate rule function; a device not in the roster is flagged on a tracked household and never on an untracked one.
- **UT-6** — the rendered Markdown matches the agreed format for the summary, per-household table, per-person session detail, anomalies and trend.
- **UT-7** — the module runs end to end, a failed refresh exits non-zero with a "report not generated" note, the README states the cron line, and the registry docs and diagram are updated.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `docs/plan/TODOS.md` and the `CONTEXT.md` plan list, and add one line to the session log. When
the whole story is done, archive it with `python scripts/dev/archive_completed_story.py household-usage-tracking`.
