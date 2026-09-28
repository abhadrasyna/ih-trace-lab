# Project taxonomy — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: PT-1, PT-2, PT-3, PT-4, PT-5, PT-6, PT-7, PT-8.**

- [ ] **PT-1** — `docs/guides/project-taxonomy.md`: five categories + `github_copilot` examples | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-2** — same doc + `structure.md`: per-category folder skeleton (Rule A/Rule B) + submodule-vs-plain-folder rule | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff
  review | SHA: <—>
- [ ] **PT-3** — same doc: new-work checklist (new folder AND new script) with mandatory prior-art search | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA:
  <—>
- [ ] **PT-4** — `scripts/dev/check_project_taxonomy.py` + tests | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **PT-5** — `AGENTS.md` + `CONTEXT.md` pointer lines | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-6** — same doc: pipeline cron-cutover procedure | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-7** — `config/data_paths.yaml` + root `data/` tree + continuous-investigation `data/`+`output/` tree + filename convention + docs-vs-knowledge guide section | Owner: AI agent (Copilot CLI)
  | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-8** — `.github/skills/investigation-doc-sync/SKILL.md`: cross-session, content-filtered case-doc sync | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review |
  SHA: <—> | **Deferred: do not start until PT-2 and PT-7 have both landed** (needs the real `investigations/<slug>/docs/` tree and `config/data_paths.yaml` templates to resolve case-doc paths
  against — nothing to sync into before then)

## Story done when

- **PT-1** — `docs/guides/project-taxonomy.md` exists with a named, one-paragraph definition for each of: pipeline, continuous investigation, one-off investigation, tool, experiment — each citing the
  specific `github_copilot` folder it is modeled on.
- **PT-2** — The same doc has a table (one row per category) listing required files/folders for that category, applying **Rule A** (a category's case-artifact folders — `docs/`, `queries/`,
  `scripts/` — live directly at the project's own root; never re-wrapped in an inner folder also named `investigations/`; raw tool inputs live in root `data/` per PT-7, not under `investigations/`)
  and **Rule B** (a slug under `investigations/` names a recurring campaign, created once; individual incoming cases are flat, ID-prefixed files within that campaign's `docs/`, never a new subfolder
  or new top-level slug per case; a case with no known campaign yet sits directly as `investigations/<case-id>/` — no `misc/` wrapper — promoted by rename to `investigations/<campaign-slug>/<case-
  id>/` once a second related case appears); a short decision rule stating exactly when new work becomes a git submodule vs. a plain folder (the "own instructions file / independent cadence" test
  from `prompt.md`'s findings); and `structure.md` updated in the same commit so it matches the table exactly.
- **PT-3** — The same doc has a checklist a session follows before **either** creating any new top-level folder **or** writing any new script inside an existing one: (1) pick a category via the PT-1
  decision tree (folder case only), (2) delegate a sub-agent to search `docs/guides/`, `knowledge/` (once it exists), `/Users/abhadra/github_copilot` (read-only), and — for the new-script case —
  `functional-code-taxonomy`'s FCT-6 cross-project script registry for prior art on the same question, (3) only create the folder/script if no reusable prior art is found, or reuse/extend what is
  found instead.
- **PT-4** — `python scripts/dev/check_project_taxonomy.py` runs against the repo root, lists top-level dirs, and flags any that match none of the PT-2 category markers; its tests cover a fixture tree
  with one matching and one unmatched directory.
- **PT-5** — `AGENTS.md` gained one pointer line to `docs/guides/project-taxonomy.md`; `CONTEXT.md`'s "What Exists" list gained one line describing this story's status.
- **PT-6** — The same doc has a `## Pipeline cron-cutover procedure` section stating: (1) add the new cron entry pointing at the ported script's new path/venv, writing to a distinct log file, without
  touching the old entry; (2) run both in parallel for at least one full cycle of that job's own schedule (e.g. a weekly job needs at least 2 weekly runs observed, a monthly job at least 1); (3) diff
  the two jobs' output for every run in that window (a script or delegated sub-agent check, not manual eyeballing); (4) only after N consecutive matching runs, remove the old crontab entry and log the
  removal (crontab is not git-tracked, so this removal has no other record unless logged manually, e.g. one line in `CONTEXT.md` or a dedicated append-only log); (5) states explicitly: never a
  same-day swap.
- **PT-7** — `config/data_paths.yaml` exists with the 7 templates (`data_with_campaign`, `data_without_campaign`, `knowledge`, `investigation_with_campaign`, `investigation_without_campaign`,
  `investigation_data`, `investigation_output`) plus `filename_date_format`; root `.gitignore` excludes `data/`; the guide doc has a `## Input data: config, layout, and knowledge vs. docs` section
  stating the conditional tool-subfolder rule (HAR-only is normal), the mandatory "Inputs used" case-doc block, the `docs/`-mandatory-vs-`knowledge/`-optional distinction with the
  `applauseInvestigation` worked example and promotion test, the default delete-on-close-out policy for raw `data/` (explicitly scoped to campaign/case data, not a continuous investigation's own
  `investigation_data`/`investigation_output` tree), the source/tool-provenance split (not input-vs-output) for a continuous investigation's per-date pipeline, and the ISO-prefix filename convention
  (per-date snapshot / per-range snapshot / cumulative-rollup — the third being intentional, not a missing-date bug) grounded in the `ctap-smvod-session-report` and `aws-access-cli` audits;
  `structure.md` already reflects all of this from the same discussion round.
- **PT-8** — `.github/skills/investigation-doc-sync/SKILL.md` exists, modeled on `session-close`'s structure, defining: the case-scoped trigger phrase, the cursor-in-deliverable mechanism (marker
  comment in `<case-id>-<topic>.md`, not a transcript-embedded event), the `session_store_sql` content-filtered extraction query (case-id/path match, not whole-session classification), the
  fresh-subagent write step producing dated findings sections, and the separate executive-summary generation pass. Marked deferred in `tasks.md` until PT-2 and PT-7 both have SHAs — this task itself
  only needs to exist as a written spec, not be exercised against a real case.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per this project's own convention — do not leave a done story half-archived.
