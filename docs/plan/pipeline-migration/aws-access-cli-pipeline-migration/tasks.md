# aws-access-cli pipeline migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: AAM-1, AAM-2, AAM-3, AAM-4, AAM-5, AAM-6.**

- [ ] **AAM-1** — Audit `aws-access-cli/scripts/` and produce a per-file lib-vs-script classification table | Owner: AI agent | Model: n/a | Review: human read-through | SHA: <—>
- [ ] **AAM-2** — Create `src/pipelines/aws-access-cli/` skeleton + thin `run_*.py` wrappers over `src/lib/*` | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **AAM-3** — Extract the 6 SQL query classes into `query-catalog`'s catalog | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **AAM-4** — Migrate output writes to PT-7's `PathResolver` + ISO-prefix filenames | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **AAM-5** — Execute PT-6's cron-cutover procedure for the 3 live crontab entries | Owner: human (crontab access required) | Model: n/a | Review: N consecutive parallel-run matches | SHA: <—>
- [ ] **AAM-6** — Add tests for ported business-logic modules + `CONTEXT.md` pointer | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>

## Story done when

- **AAM-1** — every file under `aws-access-cli/scripts/` is classified as either a `src/lib/*` consumer point or project-specific business logic, with the FCT-1 test applied and stated per file, not
  assumed from directory name alone.
- **AAM-2** — `src/pipelines/aws-access-cli/` exists with the PT-2 skeleton, all 15 `run_*.py` entry points ported as thin wrappers, and every domain-mechanism call routed through
  `src/lib/{athena,auth,report_render}` rather than a local re-implementation.
- **AAM-3** — all 6 query classes' SQL text lives in `query-catalog`'s catalog; the pipeline's own code only builds parameters and calls the catalog, with zero inline SQL strings remaining.
- **AAM-4** — every report write goes through PT-7's `PathResolver`; every filename follows the snapshot/range/rollup convention with no ad hoc date-suffix naming left.
- **AAM-5** — all 3 crontab entries have completed PT-6's parallel-run-and-diff cycle with the required number of consecutive matches, and the old (pre-migration) crontab entries are removed with the
  removal logged per PT-6's own record-keeping requirement.
- **AAM-6** — every ported business-logic module (adoption metrics, shaka-error derivation, position-report derivation) has a happy-path + edge-case test with no live AWS/Athena calls; the epic's
  `CONTEXT.md` pointer line is added.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story list and add one line to your backlog/session-log file. When the
whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
