# Query catalog — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: QC-1, QC-2, QC-3, QC-4, QC-5, QC-6.**

- [x] **QC-1** — `queries/README.md`: folder purpose, layout, and core rules | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 47e1bac
- [x] **QC-2** — `queries/athena/`: harvest 3 reference catalogs + 3 `ctap-smvod-session-report/queries/` promoted files into deduplicated templates + `index.md` (with run-status) | Owner: AI agent
  (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 6f3823a
- [ ] **QC-3** — `queries/lightstep/`: harvest `lightstep-query-templates.md` into templates + `index.md` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA:
  <—>
- [ ] **QC-4** — `knowledge/`: port (not run) DDL-cache tooling + `knowledge/README.md` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **QC-5** — `docs/guides/query-catalog.md` protocol doc + `AGENTS.md` pointer | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **QC-6** — Tests for both harvest scripts (QC-2, QC-3) | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>

## Story done when

- **QC-1** — `queries/README.md` exists at the `queries/` root, states the folder's purpose, the `athena/`/`lightstep/` layout, and the three core rules (check `index.md` first, save as a
  parameterized template not a literal, promote to a script only when reuse needs post-processing logic).
- **QC-2** — `queries/athena/index.md` lists every distinct query shape found across the 3 reference `QUERY_CATALOG.md` mega-catalogs plus `ctap-smvod-session-report/queries/`'s 3 promoted
  finalized-query files (duplicated shapes collapsed to one row/template, tagged with all origin issues); each row's template lives at `queries/athena/<slug>.sql` with `{{placeholder}}` params, a
  header comment (purpose/tables/params/status/source), and no literal IDs; each row carries a run-status (`confirmed-run`/`drafted-not-yet-run`) so the catalog never implies an unrun draft is
  production-verified.
- **QC-3** — `queries/lightstep/index.md` lists every distinct query template found in `lightstep-query-templates.md`; each row's template lives at `queries/lightstep/<slug>.md`, preserving the native
  TQL block, purpose, tool name, and save-path convention from the source.
- **QC-4** — `knowledge/README.md` documents the DDL-cache convention (one `knowledge/<project>-athena-<db>-tables.md` per Athena database, generated not hand-written) and states plainly that
  populating one for real requires `docs/plan/tenant-registry/` to land first; the 3 ported tooling scripts are present under `scripts/athena/` and importable, but this task does not execute them
  against any live database.
- **QC-5** — `docs/guides/query-catalog.md` states the write/reuse workflow end to end (check `queries/<source>/index.md` → check `knowledge/` DDL cache → write/reuse a template → promote to a script
  only if post-processing logic is needed); `AGENTS.md` gained exactly one new pointer sentence to it, in its existing "No throwaway code in production folders" paragraph.
- **QC-6** — `pytest` covers both harvest scripts: a happy path proving 2 near-identical query shapes in a fixture catalog collapse into 1 template/index row, and an edge case proving a
  malformed/no-SQL-block input file is skipped (not raised) without corrupting the rest of the harvest.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
