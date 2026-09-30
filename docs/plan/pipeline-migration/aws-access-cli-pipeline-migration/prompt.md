# aws-access-cli pipeline migration — prompt

> Port `aws-access-cli`'s scheduled Athena adoption/session/shaka-error/position reports into `src/pipelines/aws-access-cli/`, replacing its local executor/auth with `src/lib/*`, its SQL strings with
> `query-catalog`, its flat output filenames with `project-taxonomy` PT-7's convention, and its untracked crontab entries with PT-6's cutover procedure.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/aws-access-cli` (~7,566 lines under `scripts/`) is a real, currently-running project: 15 `run_*.py` entry points, driven by 3 live system-crontab entries
(daily/weekly/monthly — not git-tracked anywhere), that produce adoption/session/shaka-error/position reports from Athena. Its own `athena_runner/` package duplicates the executor/auth logic
`src-lib-migration`'s `athena-lib-integration` and `auth-lib-migration` stories already own; its 6 `athena_runner/queries/*.py` classes duplicate what `query-catalog` owns; its `output/` writes use ad
hoc filenames with no path-resolver. This story is the actual port — the part `functional-code-taxonomy`'s audit only pointed at, never executed.

## Scope guard

**In bounds:** creating `src/pipelines/aws-access-cli/` (skeleton, thin `run_*.py` wrappers, business-logic modules for adoption metrics / shaka errors / position report, tests), moving the 6 SQL
query classes' text into `query-catalog`'s catalog, replacing output writes with PT-7's `PathResolver` + ISO-prefix convention, and executing PT-6's cron-cutover procedure for the 3 live crontab
entries.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/aws-access-cli` (read-only reference — never edited); `src/lib/*` module internals (consumed as-is from `src-lib-migration`, not
modified here); `query-catalog`'s catalog format/ownership rules (consumed as-is); any change to `ctap-smvod-session-report` or its sibling story.

## Session-start load hints

- `docs/plan/project-taxonomy/structure.md` — the exact `src/pipelines/<slug>/` skeleton and the `data_paths.yaml` template names this story's output-migration task must match.
- `docs/plan/project-taxonomy/stories.md` PT-6 (cron-cutover procedure) and PT-7 (path/filename convention) — read before AAM-4 or AAM-5.
- `docs/plan/src-lib-migration/README.md` — confirms which `src/lib/*` modules exist and their import surface, before AAM-2.
- `docs/plan/query-catalog/` (its own `stories.md` for the catalog file-per-query convention) — read before AAM-3.
- `/Users/abhadra/github_copilot/aws-access-cli/scripts/` — the source tree being ported; read the specific files a task names, not the whole tree at once.

## Task overview

- **AAM-1** — Audit + per-file lib-vs-script classification table for all of `scripts/`.
- **AAM-2** — `src/pipelines/aws-access-cli/` skeleton + thin `run_*.py` wrappers using `src/lib/{athena,auth,report_render}`.
- **AAM-3** — SQL extraction: 6 query classes → `query-catalog`'s catalog.
- **AAM-4** — Output-path migration to PT-7's `PathResolver` + ISO-prefix filenames.
- **AAM-5** — Cron-cutover for the 3 live crontab entries per PT-6.
- **AAM-6** — Tests for the ported business-logic modules + `CONTEXT.md` pointer.

## Definition of done

`src/pipelines/aws-access-cli/` exists, is fully tested, imports `src/lib/*` for every domain-mechanism concern, has no SQL string literals (all cataloged), writes only PT-7-convention filenames, and
its 3 crontab entries have completed PT-6's cutover with the old entries removed and the removal logged. No file under `/Users/abhadra/github_copilot` was touched.

## Perspectives not covered

This story does not address whether `aws-access-cli`'s 11 adoption metric *definitions* are still business-correct — it ports them verbatim; a metric-correctness review is a separate, unscoped concern
that belongs to whoever owns the adoption-reporting product requirements, not this migration.
