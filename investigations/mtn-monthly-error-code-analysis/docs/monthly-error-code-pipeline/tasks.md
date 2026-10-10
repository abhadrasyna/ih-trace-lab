# Monthly error code pipeline — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: MEC-1, MEC-2, MEC-3, MEC-4, MEC-5.**

- [ ] **MEC-1** — define error-code source and count grain; add catalog query | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-2** — per-OpCo monthly Athena pull script | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-3** — cross-OpCo aggregation into the monthly report | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-4** — month-over-month comparison | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-5** — finalize runbook, usage.md, SCRIPTS.md | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **MEC-1** — the table, error field and count grain are documented, and a catalog query renders for any OpCo and month.
- **MEC-2** — one command pulls a month for one or all OpCos into `data/athena/<OPCO>/YYYY-MM/`.
- **MEC-3** — per-OpCo and all-OpCo monthly report CSVs exist under `output/`.
- **MEC-4** — a month-over-month diff report exists for any two months.
- **MEC-5** — `usage.md` documents every script and the run order, and `SCRIPTS.md` registers them.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to the backlog/session-log file. When the whole story is
done, archive it per the repo convention — do not leave a done story half-archived.
