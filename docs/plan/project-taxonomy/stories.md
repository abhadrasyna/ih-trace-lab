# Project taxonomy — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `PYTHON_DESIGN.md`. After each task: set `SHA:` on the
> task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

See `structure.md` (this story's own folder) for the canonical target tree every task below must stay consistent with — it is the single source of truth for layout; if it and any task spec below ever
disagree, `structure.md` wins and the task spec must be corrected to match.

---

## PT-1 — `docs/guides/project-taxonomy.md`: five categories + `github_copilot` examples

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — new file

**What to implement:**

1. Header matching `docs/guides/git-multi-account-auth.md`'s tone (short intro paragraph, no plan-tracking checkboxes — this is a reference doc, not a story file).
2. A `## Categories` section defining exactly five categories, one paragraph each:
   - **Pipeline** — recurring, scheduled data collection/reporting with no open-ended investigation question. Example: `github_copilot/aws-access-cli` (cron-scheduled Athena adoption/session reports,
     SSO refresh).
   - **Continuous investigation** — an open-ended, ongoing data-gathering + analysis effort tied to a live product question, expected to run for months. Example:
     `github_copilot/ctap-smvod-session-report` (already a submodule).
   - **One-off investigation** — a bounded case with a start and an end (a specific incident, a specific third-party report). Example: `github_copilot/applauseInvestigation`,
     `github_copilot/mtn-zm-session-device-investigation`.
   - **Tool** — reusable software with its own interface/protocol, actively maintained and enhanced across many callers. Example: `github_copilot/oasis-athena-mcp` (MCP server),
     `github_copilot/mtn-network-traffic` (curl-to-Python converter).
   - **Experiment** — a short-lived probe answering one narrow question, expected to be thrown away or absorbed once answered. Example: `github_copilot/vod-asset-ingestion-mapping`,
     `github_copilot/vod-playback-timing-probe`.
3. Each category paragraph ends with one sentence distinguishing it from its nearest neighbor (pipeline vs. continuous investigation: scheduled+no open question vs. open question; one-off vs.
   experiment: bounded real-world case vs. throwaway probe) — this is the actual test a session applies, not just a label.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): define the five project categories`

---

## PT-2 — same doc + `structure.md`: per-category folder skeleton (Rule A/Rule B) + submodule-vs-plain-folder rule

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — append to the file created in PT-1
- `structure.md` (this story's own folder) — update so its tree matches this task's skeleton table exactly (see `## Target folder structure` cross-reference below)

**What to implement:**

1. A `## Folder skeleton per category` table, columns `Category | Required files | Notes`, one row per PT-1 category:
   - Pipeline: `scripts/` (imports `src/lib/*` from `docs/plan/functional-code-taxonomy/`), `tests/`, a doc stating the schedule (what runs when, e.g. a cron expression or trigger description) — no
     `investigations/docs` (nothing to write up, it is not a case).
   - Continuous investigation: `AGENTS.md`-delta (or `.github/copilot-instructions.md` if a submodule), `session-info.md`, `TODO.md`, `investigations/{docs,queries}`, local `knowledge/` staging. Raw
     inputs use the same root `data/` tree PT-7 defines (this is disk-only, gitignored — a submodule boundary doesn't block reaching it).
   - One-off investigation: lives under the top-level `investigations/` category bucket, applying two rules found during the follow-up audit of `applauseInvestigation` and `vod-playback-timing-probe`
     (both independently reinvented the same nesting mistake):
     - **Rule A (no double wrap):** a project's own case-artifact folders — `docs/`, `queries/`, `scripts/` — live directly at that project's own root (`investigations/<slug>/docs/`, etc.). Never
       re-wrap them in an inner folder also named `investigations/` (i.e. never `investigations/<slug>/investigations/{docs,...}`) — that stutter is exactly the bug found in both audited projects.
       Raw tool inputs (`har`/`lightstep`/`athena`) do **not** live under `investigations/` at all — see PT-7's root `data/` tree.
     - **Rule B (campaign, not per-case folder; revised by the 2026-09-28 discussion round — supersedes the original `misc/`-catch-all wording):** a `<slug>` under `investigations/` names a
       recurring campaign or relationship (e.g. `applause` for the ongoing 3rd-party-testing relationship, `mtn-zm-device` for the Zambia device investigation), created once. Individual incoming
       cases (ticket/incident IDs) become flat, ID-prefixed files inside that campaign's `docs/` (`<case-id>-<topic>.md`, `<case-id>-executive-summary.md`) — never a new subfolder under `docs/`. A
       case with **no known campaign yet** is **not** wrapped in a `misc/` catch-all — it sits directly as `investigations/<case-id>/` (same `docs/queries/scripts/tests` skeleton, minus the campaign
       layer). Once a second related case appears, promote by renaming/moving it to `investigations/<campaign-slug>/<case-id>/` — the same promotion mechanic a `misc/` bucket would have required
       anyway, just without an extra directory nobody needs. This mirrors `scratch/`'s existing convergence-before-promotion principle. Require an explicit close-out step per case (move its docs to
       `docs/archive/`) — do not leave closed cases mixed with open ones. Raw inputs for a standalone case follow the identical promotion rule in PT-7's `data/<case-id>/` → `data/<campaign-slug>/
       <case-id>/`.
   - Tool: `src/`, `tests/`, its own `README.md`, no `investigations/` (it is not a case-tracking folder).
   - Experiment: starts in `scratch/` per this project's existing convergence rule (`scratch/SCRATCH.md`) — only gets a dedicated folder under `experiments/` if/when it converges past a single
     session's throwaway probe; never starts as its own top-level folder.
2. A `## Submodule vs. plain folder` section stating the rule found during the 2026-09-28 audit: a folder becomes a real git submodule (own `.git`, own remote, own `.github/copilot-instructions.md` if
   it needs instructions distinct from the root's) when it is a **pipeline**, **continuous investigation**, or **tool** (independent commit cadence, benefits from scoped instructions); it stays a
   **plain folder** under the root repo when it is a **one-off investigation** or **experiment** (short-lived, no benefit from a separate remote, and per `CONTEXT.md`'s constraint this project has no
   folders yet needing that split — state this is the rule for *future* work, not a migration list).
3. Update `structure.md`'s `investigations/` block in the same commit so it shows: a standalone `investigations/<case-id>/` example, at least one campaign example (`<campaign-slug>/{docs/{<case-id>-
   *.md, archive/}, queries/, scripts/, tests/}` — no `data/` here, see PT-7), and one continuous-investigation submodule example — matching this table row for row.
4. Cross-reference `docs/plan/functional-code-taxonomy/` by name for "what code a pipeline/tool/investigation's `scripts/`/`src/` folder should import" — do not restate that story's module layout
   here.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): add folder skeletons, Rule A/B, and submodule-vs-folder rule`

---

## PT-3 — same doc: new-work checklist (new folder AND new script) with mandatory prior-art search

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — append to the file created in PT-1/PT-2

**What to implement:**

1. A `## Starting new work` checklist covering two triggers — creating a new top-level folder, and writing any new script inside an existing one — because auditing actual HAR-parsing code found the
   identical loader function reimplemented four times across three projects (twice within the same project) even though every one of those projects nominally followed a "thin script, import shared
   lib" convention; the convention alone did not stop the duplication, so the checklist must fire per-script, not just per-folder:
   1. **New top-level folder:** classify the work against the PT-1 category definitions — if it doesn't clearly fit one, stop and ask (per this project's global "don't assume — ask" rule) rather than
      picking the closest label.
   2. **New top-level folder:** delegate a sub-agent (the `explore` or `task` agent type — bounded, read-only) to search, in order: `docs/guides/`, `knowledge/` (once it exists as a folder), and
      `/Users/abhadra/github_copilot` (read-only reference) for prior art answering the same or a closely related question. Give the sub-agent the concrete question, not just a category name.
   3. **New script (any category):** before writing it, delegate a sub-agent to check `docs/plan/functional-code-taxonomy/`'s FCT-6 cross-project script registry (once it exists) for an existing
      script or `src/lib/*` module doing the same or closely related thing — e.g. HAR-entry loading, CSV/report writing, Athena querying. Give the sub-agent the concrete operation the script performs,
      not the project name.
   4. If either search finds a match: reuse or extend it; do not create a new top-level folder, or a new script, duplicating it.
   5. If no match: create the folder using PT-2's skeleton for the classified category, or write the script importing `src/lib/*` as normal.
2. State explicitly why steps 2 and 3 are delegated rather than done inline — same rationale as `docs/plan/scratch-script-registry/prompt.md`'s duplicate-check delegation (keeps the search cost off
   the main session's context, makes it a named auditable step) — this checklist is that same pattern applied at whole-project scope *and* at per-script scope, not just single-script scope inside
   `scratch/`; do not re-justify it differently.
3. Cross-reference `docs/plan/functional-code-taxonomy/`'s "shared vs. specific" test (FCT-1) as the follow-up question once a match or near-match is found: if the found code operates on a domain
   mechanism (Athena, CSV/report I/O, HAR parsing) rather than a campaign/case-specific business rule, it belongs in `src/lib/`, not copied into a new script — do not restate that test here.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): add new-work checklist covering folders and scripts`

---

## PT-4 — `scripts/dev/check_project_taxonomy.py` + tests

**Files to change / create:**
- `scripts/dev/check_project_taxonomy.py`
- `tests/dev/test_check_project_taxonomy.py`
- `tests/dev/__init__.py` if not already created by another story (per `AGENTS.md`'s package convention — check before creating a duplicate)

**What to implement:**

1. `CATEGORY_MARKERS: dict[str, tuple[str, ...]]` — for each PT-1 category, the marker file(s)/folder(s) from PT-2's skeleton that identify it (e.g. continuous/one-off investigation:
   `investigations/`; tool: `src/` + own `README.md`; pipeline: `scripts/` + a schedule doc — use a `Protocol`-free simple mapping here, this is a small audit script, not a domain model warranting
   `PYTHON_DESIGN.md`'s DI treatment).
2. `classify_dir(path: Path) -> str | None` — checks a top-level directory against `CATEGORY_MARKERS`, returns the matched category name or `None` if no marker matches.
3. `find_unclassified_dirs(root: Path, ignore: tuple[str, ...]) -> list[Path]` — lists top-level directories under `root` excluding a fixed ignore set (`.git`, `docs`, `scripts`, `tests`, `scratch`,
   `logs`, `tmp`, `tooling`, `.github`, `config`, `data`, `knowledge` — the last three are cross-cutting infra defined by PT-7, not a category instance to classify) whose `classify_dir` result is
   `None`.
4. `main()` — `argparse` with `--root` (default: repo root); prints each unclassified directory with a one-line hint to run PT-3's checklist before deciding its category; exits non-zero only if asked
   with `--strict` (default off — this is advisory, not a commit-blocking gate, since no folders exist yet to enforce against).

**Tests (no network, no real external directories outside `tmp_path`):**
- `test_classify_dir_matches_investigation_marker` / `test_classify_dir_returns_none_for_unrecognized_layout`
- `test_find_unclassified_dirs_skips_ignored_and_flags_unmarked` — fixture tree with one classified dir, one unclassified dir, and one ignored dir (e.g. `docs/`); assert only the unclassified one is
  returned.

**Commit:** `feat(project-taxonomy): add check_project_taxonomy.py audit script`

---

## PT-5 — `AGENTS.md` + `CONTEXT.md` pointer lines

**Files to change / create:**
- `AGENTS.md` — add one pointer line (placement: near the existing docs/plan story-tracking section, per its existing structure)
- `CONTEXT.md` — add one line to "What Exists"

**What to implement:**

1. `AGENTS.md`: one sentence pointing to `docs/guides/project-taxonomy.md` as the reference for classifying new work and picking its folder skeleton before creating any new top-level folder. No
   taxonomy content duplicated into `AGENTS.md` itself.
2. `CONTEXT.md`: one new bullet under "What Exists" in the same style as the existing `tenant-registry`/`query-catalog` bullets — story slug, one-line summary, current status (implemented once PT-1
   through PT-7 are all checked; reference the first unchecked task id if not yet fully done at the time this task runs).

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): point AGENTS.md and CONTEXT.md at the new guide`

---

## PT-6 — same doc: pipeline cron-cutover procedure

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — append a new `## Pipeline cron-cutover procedure` section

**What to implement:**

1. Open with the concrete grounding fact (do not generalize it away): `aws-access-cli` has three live system-crontab entries (daily/weekly/monthly report jobs) hardcoding its current
   `github_copilot/aws-access-cli` path and `.venv`. Crontab is not git-tracked — no diff/PR review ever sees an edit to it, unlike every other change this project makes.
2. State the procedure as a numbered, mandatory checklist for any future story that ports a **pipeline**-category project (per PT-1) to a new location:
   1. Add the new cron entry pointing at the ported script's new path/venv, writing output to a distinct log file (e.g. suffix `_v2`). Do not edit or remove the old entry yet — both run in parallel.
   2. Let both run for at least one full cycle of that job's own schedule before comparing anything — a daily job needs several daily runs, a weekly job needs at least 2 weekly runs, a monthly job
      needs at least 1 monthly run. A shorter window has not actually exercised the job's real schedule.
   3. Diff the two jobs' output for every run in that window — row counts, key metrics, or a full content diff depending on the report type. This must be a script or a delegated sub-agent check, not
      manual eyeballing, since these are unattended automated reports and a person is not watching every run.
   4. Only after N consecutive matching runs (state a default, e.g. 3, adjustable per job), remove the old crontab entry. Because crontab has no other change record, log the removal manually — one
      line in `CONTEXT.md` or a dedicated append-only log naming the job, the date, and the verification window that justified it.
   5. State explicitly, as the closing rule: **never a same-day swap.** A same-day cutover risks a silently broken daily/weekly/monthly report going unnoticed for a full cycle, which is strictly worse
      than the duplication this taxonomy exists to remove.
3. One closing sentence noting this procedure is documentation only here — no pipeline has been ported yet, so no crontab edit happens as part of this task or this story.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): add pipeline cron-cutover procedure`

---

## PT-7 — `config/data_paths.yaml` + root `data/` tree + continuous-investigation `data/`+`output/` tree + filename convention + docs-vs-knowledge guide section

**Grounding:** found during the 2026-09-28 discussion round auditing `applauseInvestigation`, `github_copilot/investigations`, and `ctap-smvod-session-report`. Three prior mistakes this task closes:
- `applauseInvestigation` already keeps raw tool inputs (`investigations/data/<case-id>/{lightstep,har,athena}`, 1.6GB, gitignored wholesale — confirmed via its own `.gitignore`) and a project-local
  `knowledge/` with genuinely reusable findings (`lightstep-span-attributes-by-service.md`, `applause-csv-household-id-gotchas.md`) — a case-independent-knowledge folder PT-2's skeleton table never
  accounted for on the one-off-investigation row.
- `github_copilot/investigations` (a separate, older project) shows the failure mode of *not* having any convention: ad hoc top-level buckets invented per data-type (`athenaCSV/`, `spancsv/`,
  `xmls_or_mpd/`, `har/`), zero case-id/campaign grouping, ~25 unrelated HAR files flat in one folder distinguishable only by inconsistent filenames. This is the negative example the design below
  prevents, not a variant to reconcile with.
- `ctap-smvod-session-report` (a continuous-investigation submodule, not a campaign/case) mixes a true manual input (3 hand-exported Lightstep CSVs/day — no live API) with a later pipeline step's
  own Athena output, re-read as the next step's input, under one undifferentiated `inputCSV/` folder name. Its `aws-access-cli` sibling (pure pipeline, no persisted input — queries Athena live and
  writes straight to `output/<TENANT>/{daily,monthly,weekly}/`) confirms this input/output ambiguity is specific to a chained, per-date pipeline and does not apply to a pipeline with no manual Step
  1. This is why `investigation_data`/`investigation_output` below split by *source/tool provenance*, not input-vs-output.

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — append a new `## Input data: config, layout, and knowledge vs. docs` section
- `config/data_paths.yaml` — new file
- `.gitignore` (repo root) — new file if it doesn't exist, or one appended line
- `structure.md` (this story's own folder) — already updated in this same discussion round (see the `data/`, `config/`, and `knowledge/` blocks)

**What to implement:**

1. **`config/data_paths.yaml`** is the single source of truth for input-data shape — scripts never hardcode it:
   ```yaml
   data_root: data
   knowledge_root: knowledge
   investigations_root: investigations
   tools: [har, lightstep, athena]
   templates:
     data_with_campaign:              "{data_root}/{campaign}/{case_id}/{tool}"
     data_without_campaign:           "{data_root}/{case_id}/{tool}"
     knowledge:                        "{knowledge_root}/{tool}"
     investigation_with_campaign:     "{investigations_root}/{campaign}"
     investigation_without_campaign:  "{investigations_root}/{case_id}"
     investigation_data:              "{investigations_root}/{continuous_investigation_slug}/data/{tool}"
     investigation_output:            "{investigations_root}/{continuous_investigation_slug}/output"
   filename_date_format: "%Y-%m-%d"     # ISO, prefix position — see the filename-convention point below
   ```
   The last two templates are for a **continuous-investigation submodule** (e.g. `ctap-smvod`), not a campaign/case — found during the same 2026-09-28 round auditing `ctap-smvod-session-report`'s
   `inputCSV/`, which mixes true manual exports with a later step's own re-read Athena output under one folder name. Root `data/`'s `{campaign}/{case_id}/{tool}` split is input-vs-nothing (a case
   either has saved data for a tool or it doesn't); `investigation_data`'s split is *source/tool provenance*, not input-vs-output — because in a repeating per-date pipeline, step N's output is
   legitimately step N+1's input, and forcing a rename between an "inputs" and "outputs" folder mid-chain for that reason alone buys nothing. Deliverables (post-merge, final per-date reports) stay
   in `investigation_output`, never in `investigation_data` — only raw/intermediate per-tool pulls belong under `investigation_data/{tool}`. `functional-code-taxonomy`'s FCT-7 owns the
   `src/lib/paths/` resolver that reads this file — this task only owns the config file and the guide prose; do not duplicate resolver code here.
2. **Root `data/` tree**, gitignored wholesale in one root `.gitignore` line (`data/`) — replacing the per-project duplicated `.gitignore` lines the reference projects each reinvented:
   - `data/<campaign-slug>/<case-id>/{har,lightstep,athena}/` for a campaign case.
   - `data/<case-id>/{har,lightstep,athena}/` for a standalone case (no `misc/` wrapper — see PT-2's revised Rule B); promoted to the campaign form once a 2nd related case appears, identical promotion
     mechanic to `investigations/<case-id>/` → `investigations/<campaign-slug>/<case-id>/`.
   - Each tool subfolder (`har/`, `lightstep/`, `athena/`) is present **only if that tool was actually used and something was saved** — a HAR-only case is normal, not a gap. A manual/interactive
     Lightstep or Athena query that produced nothing worth saving on disk leaves no folder here; if a manual query *did* produce something worth keeping (a screenshot, a copy-pasted export), it still
     goes in the matching tool subfolder, tagged as manual in its filename or a short note, so the resolver still finds it.
3. **Mandatory "Inputs used" block** in every case doc (`investigations/*/docs/<case-id>-*.md`), stating for each of the three tools whether it was used, and if so, saved-to-disk vs. manual-only —
   e.g.:
   ```
   - HAR: yes (data/<campaign-or-case-id>/<case-id>/har/)
   - Lightstep: manual query only, not saved — see "Lightstep findings" section below
   - Athena: no
   ```
   This is mandatory, not optional prose, because absence of a saved-CSV folder is otherwise indistinguishable from "wasn't checked" — a methodology gap, not a file-presence gap.
4. **`docs/` vs. `knowledge/` distinction**, stated explicitly with the worked example found in `applauseInvestigation`:
   - `investigations/*/docs/<case-id>-*.md` is the **mandatory, per-case deliverable** — every investigation produces one, it is what gets shared outside this project to explain what happened, and it
     stays tied to that case's ticket/household/device IDs forever. Cite `applauseInvestigation/investigations/docs/7231547-android-secure-decoder-failure.md` as the concrete example: household ID,
     device ID, ticket status, per-case timeline — useless to any other case except as precedent.
   - `knowledge/<tool>/` is an **optional, opportunistic side-effect** — most cases produce nothing for it; never write to it just to "use" the folder. Cite
     `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` as the concrete example: it names the case it was gathered during (7231547) in its own header, while being written so
     that ticket number is irrelevant to using it — e.g. "`deviceType` tag is unreliable for platform detection, confirmed via HAR cross-check" is true on any future case touching that service.
   - **Promotion test:** would this fact still be true and useful on a *different* ticket, with different household/device IDs? If yes → `knowledge/<tool>/`. If it only makes sense with this ticket's
     specifics → stays in `docs/`.
5. **Close-out policy** (default, stated as adjustable per campaign if a real recurring re-verification need shows up): once a case's `docs/` write-up (and any `knowledge/` promotion) is complete,
   **delete** its raw `data/.../​<case-id>/` — do not archive it indefinitely. Grounding fact: one campaign's raw data alone already reached 1.6GB; an archive-forever default does not scale across many
   campaigns and many cases the way a small, distilled `docs/`+`knowledge/` does. This policy does **not** apply to `investigation_data`/`investigation_output` (a continuous-investigation submodule's
   own per-date pipeline tree) — there is no "case close" event on an ongoing daily pipeline; that tree's retention is the submodule's own concern (e.g. a rolling window), not this story's.
6. **Filename convention for date-keyed artifacts**, found necessary auditing `ctap-smvod-session-report`'s existing `DDMMYYYY`-suffix files (`athena_session_01082026.csv`) — ambiguous (reads as
   either DD-MM or MM-DD) and unsortable (a filename *suffix* means `ls`/glob order is alphabetical, not chronological: `_01082026` sorts before `_10072026`, i.e. August before July). Reuses the ISO
   date already established by `scratch-script-registry`'s `scratch/<YYYY-MM-DD>_<topic>_<purpose>.py` convention rather than inventing a third format, moved to a **prefix** so directory listings sort
   chronologically for free. Three distinct file categories, not one rule:
   - **Per-date snapshot** (one file per single date, the common case under `investigation_data`/`investigation_output`): `YYYY-MM-DD_<artifact>.csv` — e.g. `2026-08-01_ctap.csv` inside
     `data/lightstep/` (tool name dropped from the filename — the parent folder already carries it), `2026-08-01_position_report.csv` inside `output/`.
   - **Per-range snapshot** (computed once for a fixed range, not re-run daily): `YYYY-MM-DD_YYYY-MM-DD_<artifact>.csv` — e.g. `2026-08-02_2026-08-08_position_report.csv`. A ticket/case tag, if one
     applies, is a **trailing** suffix, never an infix between metric and dates (`ctap-smvod-session-report`'s existing `position_report_1003_02082026_08082026.csv` buries `1003` mid-name, breaking
     any simple `<date(s)>_<artifact>` parse) — corrected form: `2026-08-02_2026-08-08_position_report_1003.csv`.
   - **Cumulative/rollup** (a single file appended with new rows every run, the date living as a *column*, not the filename — this is intentional, not a missing-date bug; confirmed against
     `aws-access-cli`'s `output/<TENANT>/{monthly,weekly}/adoption_session_report.csv`, where the cadence folder itself signals "this is a rollup" so a bare name is unambiguous there): when there is
     no cadence folder to carry that signal (e.g. `ctap-smvod`'s flat `output/mtn_escalation_all_dates.csv`), the filename needs an explicit rollup marker — standardize on a trailing `_rollup` (or
     keep the existing `_all_dates`) tag so it is never mistaken for a per-date snapshot file that simply forgot its date.
   `aws-access-cli`'s root-level `output/*_21092026.csv` files repeat the same ambiguous `DDMMYYYY`-suffix mistake — cited here as a second confirming negative example, not a pattern to copy.
7. Cross-reference `functional-code-taxonomy`'s FCT-7 by name for "the code that reads this config" — do not restate the resolver's function signatures here.

**Tests:** none — docs/config-only (the resolver's tests live under FCT-7).

**Commit:** `docs(project-taxonomy): add config/data_paths.yaml, root data/ tree, and docs-vs-knowledge guide section`

---

## PT-8 — `.github/skills/investigation-doc-sync/SKILL.md`: cross-session, content-filtered case-doc sync

**Deferred:** do not start until PT-2 and PT-7 have both landed — this task syncs findings *into* the real `investigations/<slug>/docs/<case-id>-*.md` tree and resolves paths via
`config/data_paths.yaml`'s templates; neither exists before then.

**Grounding:** found during a 2026-09-28 discussion round on how PT-2's mandatory case docs (`<case-id>-<topic>.md`, `<case-id>-executive-summary.md`) actually get written without either (a)
deferring all write-up to investigation close (loses the ability to hand off a paused case — see the `Status: IN PROGRESS` pattern already in `applauseInvestigation`'s docs) or (b) manual
mid-investigation formatting discipline drifting in style session to session. Modeled directly on this repo's own `session-close` skill (`.github/skills/session-close/SKILL.md`), which proves
Copilot CLI already persists every tool call and assistant turn to `~/.copilot/session-state/<session-id>/events.jsonl` for free — no manual dump needed, only an extraction pass. Differs from
`session-close` in one load-bearing way: `session-close` audits *one bounded session's transcript*; an investigation spans *many* sessions, most of which have nothing to do with any given case, so
the trigger must be content-filtered (does this window reference case X's path/ticket-id?), never session-filtered (is this whole session an investigation?).

**Files to change / create:**
- `.github/skills/investigation-doc-sync/SKILL.md` — new file

**What to implement:**

1. **Trigger phrase, explicit and case-scoped** — e.g. "investigation checkpoint `<case-id>`" (mirroring `session-close`'s trigger-phrase convention) — invoked only when the analyst knows
   case-specific work just happened; never auto-fired at every session end.
2. **Cursor lives in the deliverable, not the transcript** — a marker comment at the top of `<case-id>-<topic>.md`, e.g. `<!-- last-synced: 2026-09-14T10:22:00Z -->`. `session-close` finds its
   window via `skill.invoked` events inside one transcript; that breaks here because the relevant sessions differ each invocation. Each run reads this timestamp as the cursor and rewrites it after
   syncing.
3. **Extraction filters by content, across sessions** — query `session_store_sql` (`local` scope; `tool_executions`/`session_files`/`turns`) for rows with `started_at`/`timestamp` after the cursor
   whose arguments or file paths contain the case-id or its resolved data path (`investigations/<slug>/data/<case-id>` per `config/data_paths.yaml`, or the bare ticket number in an Athena/Lightstep
   query argument) — regardless of which session emitted them. A session contributing zero matching rows (e.g. an unrelated docs/refactoring session) is silently skipped, not flagged as an error.
4. **Fresh subagent does the writing** — per `session-close`'s own stated reason (bounded extraction cost, not a full context clone): a subagent receives only the matched rows, appends one new dated
   `## <finding> (<date>)` section per distinct finding to `<case-id>-<topic>.md` (finding + evidence table + a bolded conclusion sentence — the style already established in
   `applauseInvestigation/investigations/docs/7231763-android-resume-watching-latency.md`), and updates the cursor.
5. **Executive summary is a separate, cheaper pass** — once `<case-id>-<topic>.md` has multiple dated sections, generating `<case-id>-executive-summary.md` condenses that already-clean markdown
   file (headline finding, ruled-out table, recommendation — per `7231763-executive-summary.md`'s and `7232657-executive-summary.md`'s shape), not the raw transcript — invoked as its own trigger
   phrase (e.g. "investigation summary `<case-id>`"), typically at close-out, not every checkpoint.
6. Cross-reference `docs/plan/project-taxonomy/structure.md`'s `investigations/` block and PT-7's "Inputs used" mandatory block by name — this skill populates those files, it does not redefine
   their shape.
7. **Session-provenance table with both `cwd` and a derived `Case/Campaign` column** — grounded in a cross-check of `applauseInvestigation/session-info.md` (see
   `applauseInvestigation/AGENTS.md`'s "append a row every session" convention): of 18 real Copilot CLI sessions with `cwd = applauseInvestigation`, only 8 rows ever got logged (the manual
   "remember to append" step silently stopped being followed after 2026-08-16) — proving a purely-manual provenance log decays exactly like `session-history-summary.md` did. `cwd` alone is
   currently low-signal: Copilot CLI records it once per session at launch, and today all 18 sessions share the identical value `/Users/abhadra/github_copilot/applauseInvestigation` because no
   session was ever launched from inside a nested `investigations/<campaign-slug>/`. It is kept as its own column anyway — cheap, already present in `sessions`, and it becomes genuinely useful the
   day the "launch from inside the case/campaign folder" convention (see PT-3's checklist) is actually followed, at which point it will show the nested path directly without any extra derivation.
   Until then (and permanently, for sessions that don't follow that convention, or that touch more than one case), the authoritative column is `Case/Campaign`, derived from `session_files`
   path-matching (the same source step 3 already queries): match each session's touched paths against `investigations/(docs|data)/<case-id>-*` / `investigations/<campaign-slug>/`, falling back to
   `—` for sessions that touched no case-scoped file (scaffolding, knowledge-only, or pure Q&A sessions). Worked example, reconstructed from real `applauseInvestigation` session history:

   | Date | Session ID | cwd | Case/Campaign |
   |---|---|---|---|
   | 2026-08-14 | `abe1165e` | `applauseInvestigation` | *(scaffold — no case yet)* |
   | 2026-08-14 | `47617f46` | `applauseInvestigation` | `7231547` |
   | 2026-08-14 | `3eb92693` | `applauseInvestigation` | `7231547` |
   | 2026-08-14 | `80a4af33` | `applauseInvestigation` | `7231763` |
   | 2026-08-25 | `a987b3ed` | `applauseInvestigation` | `7231763` |
   | 2026-08-25 | `bf16595c` | `applauseInvestigation` | `7233017` |
   | 2026-08-20 | `a2e0d27a` | `applauseInvestigation` | *(no files edited — Q&A only)* |

   (`cwd` is uniform in this table today for the reason above — it is not dead weight, it is a column waiting for the launch-directory convention to populate it with real variation, same as
   `ctap-smvod-session-report`/`mtn-zm-session-device-investigation` already show non-uniform `cwd` values across different projects.) This lets a session pick up a paused case (e.g. `7231763`,
   `7233017` — each revisited across non-consecutive sessions days apart) by scanning one table instead of opening every session-state transcript, and the table itself is regenerated by the same
   sync pass (step 3/4), so it inherits that pass's freshness — it is not a second manually-maintained log.
8. **Multi-session combine-by-case, not overwrite** — grounded in case `7231763`, which real history shows was worked across **two sessions 11 days apart**: `80a4af33` (2026-08-14, first HAR/Lightstep
   latency pass: ruled out CTAP backend, profiled the `session-guard` proxy hop and MPD/CDN timeline, captured client IP, then explicitly closed with "save state, pick next latency issue") and
   `a987b3ed` (2026-08-25, a QA-requested reproduction run: new HAR + console logs for `run2`, re-derived the same FCID trace-pull technique, produced a fresh tap-to-playing timeline measured at
   9.35s, and converted it to a Jira-formatted comment). Because extraction is content-filtered per case-id (step 3) and each run only appends what's new since the cursor (step 2/4), the two
   sessions land as two independent dated sections in `7231763-android-resume-watching-latency.md` — never overwriting each other even though they're 11 days and one paused-and-resumed cycle apart.
   The executive-summary pass (step 5) then condenses *both* dated sections into one `7231763-executive-summary.md`, e.g.:

   > **Case 7231763 — Resume-watching latency (2 investigation rounds: 2026-08-14, 2026-08-25)**
   > - Round 1 (Aug 14): CTAP/backend ruled out; `session-guard` proxy and MPD/CDN timeline profiled; client IP captured.
   > - Round 2 (Aug 25, QA repro `run2`): same latency pattern reproduced; full tap→playing timeline measured at 9.35s; round-1's FCID trace-pull technique reused.
   > - **Conclusion:** consistent root cause confirmed across both reproductions.

   This is the combined-summary behavior the skill must guarantee whenever multiple sessions target the same case/campaign, regardless of how many days apart they run or whether `cwd` matches
   across them.

**Tests:** none — a skill file, not application code; verification is a real invocation against a fixture case once PT-2/PT-7 land (out of scope for this task itself).

**Commit:** `docs(project-taxonomy): add investigation-doc-sync skill (deferred until PT-2/PT-7 land)`
