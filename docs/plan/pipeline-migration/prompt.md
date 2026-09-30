# Pipeline migration — router

Route to this epic's stories once you know which project/task you're picking up. This file has no tasks of its own — see each story's own `prompt.md` for its routing rules.

## Hard gate — read before starting any story

Both stories in this epic are blocked until these land:

1. `docs/plan/project-taxonomy/` — PT-1 (category definitions), PT-2 (folder skeletons), PT-7 (`config/data_paths.yaml` + filename convention) at minimum; `aws-access-cli-pipeline-migration`
   additionally needs PT-6 (cron-cutover procedure) before its cutover task.
2. `docs/plan/src-lib-migration/` — the `src/lib/*` modules both stories import must exist and be tested first.
3. `docs/plan/query-catalog/` — the SQL-catalog location both stories hand their query files to must exist first.

If any of these are not yet ✅ done, stop and pick up that story instead — do not re-derive folder skeletons, filename conventions, or SQL-catalog locations locally; this epic only consumes them.

## Story selection

| If you're working on… | Go to |
|---|---|
| `aws-access-cli` (scheduled Athena adoption/session/shaka-error reports, cron-driven) | `aws-access-cli-pipeline-migration/prompt.md` |
| `ctap-smvod-session-report` (recurring, part-manual/part-Athena investigation campaign) | `ctap-smvod-investigation-migration/prompt.md` |

## Invariant

Never create, edit, or delete any file under `/Users/abhadra/github_copilot` — it is read-only reference for both stories in this epic.
