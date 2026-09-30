# Project taxonomy

Use this guide before creating any new top-level work folder in `ih-trace-lab`. It names the four project categories this repo accepts, the boundary between them, and the folder/document rules later
sections build on.

## Categories

**Pipeline** — recurring, scheduled data collection or reporting with no open-ended investigation question and no case deliverable to write up. The model is `github_copilot/aws-access-cli`:
cron-driven Athena adoption/session reports plus SSO refresh automation. The nearest neighbor is an investigation; the deciding test is simple: if there is no live product question and no mandatory
case doc, it is a pipeline, not an investigation.

**Investigation** — a campaign or case tied to a live product question, whether that work closes as a bounded case or continues as a recurring, no-close-event campaign with dated outputs. The model is
`github_copilot/applauseInvestigation`, `github_copilot/mtn-zm-session-device-investigation`, and `github_copilot/ctap-smvod-session-report`, with the last one treated here as a plain folder rather
than a separate category or submodule. The nearest neighbors are pipelines and experiments: unlike a pipeline it has an open question plus mandatory docs, and within the category the distinction is
case-close-out versus rolling retention, not a fifth top-level label.

**Tool** — reusable software with its own interface or protocol, kept alive across many callers rather than one campaign's immediate question. The model is `github_copilot/oasis-athena-mcp` and
`github_copilot/mtn-network-traffic`, both maintained as software products rather than case folders. The nearest neighbor is an experiment; if the output needs a stable interface other work can call
and you expect ongoing enhancement, it is a tool, not a throwaway probe.

**Experiment** — a short-lived probe answering one narrow question, expected to be thrown away or absorbed once it proves or disproves that point. The model is
`github_copilot/vod-playback-timing-probe`, while noting the open tension recorded in `docs/plan/reference-code-gap-migration/README.md` that this example may read more like a tool on a later pass.
The nearest neighbor is an investigation; if the work is a disposable probe rather than a real product question with mandatory case docs, it is an experiment, not an investigation.

## Folder skeleton per category

| Category | Required files | Notes |
|---|---|---|
| Pipeline | `scripts/`, `tests/`, `README.md` documenting schedule/trigger | No case docs; `scripts/` stays thin over shared code from `docs/plan/functional-code-taxonomy/`. |
| Investigation | `investigations/<slug>/` with `docs/`, `scripts/`, `tests/` | Applies Rule A and Rule B below; cross-campaign queries stay in repo-root `queries/`. |
| Tool | `src/`, `tests/`, `README.md` | Software interface, not a case folder; imports shared modules from `docs/plan/functional-code-taxonomy/`. |
| Experiment | Starts in `scratch/`; only later earns `experiments/<experiment-slug>/` | Never begins as a dedicated top-level folder. |

**Rule A: no double wrap.** An investigation project's own `docs/` and `scripts/` live directly under its root. Never create `investigations/<slug>/investigations/{docs,...}`. Raw inputs live in root
`data/` per PT-7, not under an inner `investigations/` folder.

**Rule B: campaign slug, flat case docs.** A campaign slug is created once and keeps flat, ID-prefixed case docs. A standalone case with no known campaign yet lives directly as
`investigations/<case-id>/` and is promoted by rename once a second related case appears. Bounded cases archive their docs at close-out, while recurring campaigns keep dated docs and may add optional
`data/`, `output/`, and `RETENTION.md` siblings when they run a no-close-event per-date pipeline.

## Continuous investigations are plain folders

The 2026-09-28 audit did not find any concrete benefit tied to `github_copilot/ctap-smvod-session-report`'s existing submodule boundary: no hook, workflow, or review path depended on a separate git
root. Its only real difference from a bounded campaign is a recurring `data/` plus `output/` pipeline tree, which PT-7 already handles with config-driven path templates. In this repo, pipeline,
investigation, tool, and experiment are therefore plain folders by default; a real git submodule is justified only by an external fact such as different ownership or an already-published remote, not
by the category label itself.

## Starting new work

Use this checklist before either creating a new top-level folder or writing a new script inside an existing one.

1. **New top-level folder:** classify the work with the four category definitions above. If it does not clearly fit one category, stop and ask rather than guessing.
2. **New top-level folder:** delegate a bounded read-only sub-agent to search `docs/guides/`, `knowledge/` once it exists, and `/Users/abhadra/github_copilot` for prior art on the concrete question
   being answered, not just the category name.
3. **New script in any category:** delegate a bounded sub-agent to check `docs/plan/functional-code-taxonomy/`'s FCT-6 cross-project script registry for an existing script or `src/lib/*` module doing
   the same operation, such as HAR-entry loading, CSV/report writing, or Athena querying.
4. If either search finds a match, reuse or extend it rather than creating a duplicate folder or script.
5. If no match exists, create the folder with the skeleton above or write the new script as a thin consumer of shared code.

Steps 2 and 3 are delegated for the same reason documented in `docs/plan/scratch-script-registry/prompt.md`: the search cost stays out of the main session context, and the duplicate-check remains a
named, auditable step instead of an easy-to-skip intention. Once a match or near-match is found, apply `docs/plan/functional-code-taxonomy/`'s shared-vs-specific test: domain-mechanism code belongs in
`src/lib/`, not as another copied local script.

## Pipeline cron-cutover procedure

`github_copilot/aws-access-cli` currently has three live system-crontab entries for daily, weekly, and monthly report jobs, each hardcoding that repo's path and `.venv`. Crontab is not git-tracked, so
an edit there gets none of the diff or review visibility the code itself receives.

Use this checklist whenever a future story ports a pipeline-category project to a new location:

1. Add the new cron entry pointing at the ported script's new path and venv, and send it to a distinct log file such as a `_v2` variant. Do not edit or remove the old entry yet; both jobs run in
   parallel first.
2. Let both entries run for at least one full cycle of that job's real schedule before comparing results. Daily work needs several daily runs, weekly work needs at least two weekly runs, and monthly
   work needs at least one monthly run.
3. Diff the two jobs' output for every run in that window, using row counts, key metrics, or a full content diff as the report demands. This must be a script or delegated sub-agent check, not manual
   eyeballing.
4. Only after a default of three consecutive matching runs, adjusted upward if the job needs it, remove the old crontab entry. Because crontab has no built-in change record, log that removal manually
   in `CONTEXT.md` or a dedicated append-only log with the job name, date, and verification window.
5. **Never a same-day swap.** A same-day cutover risks a silently broken daily, weekly, or monthly report going unnoticed for a full cycle, which is worse than a temporary duplicate run.

This section is documentation only in this story. No pipeline has been ported yet, so this task does not edit any live crontab entry.

## Input data: config, layout, and knowledge vs. docs

`config/data_paths.yaml` is the single source of truth for input-data layout. Scripts must read it through the future `docs/plan/functional-code-taxonomy/` FCT-7 resolver rather than hardcoding
`data/`, `knowledge/`, or `investigations/` paths themselves. The recurring-campaign templates there are for a no-close-event campaign such as `ctap-smvod`: `investigation_data` keeps raw or
intermediate per-tool pulls by provenance, while `investigation_output` keeps final per-date deliverables.

Root `data/` is gitignored wholesale and groups saved raw inputs by case, then by tool: `data/<campaign-slug>/<case-id>/{har,lightstep,athena}/` for a campaign case, or
`data/<case-id>/{har,lightstep,athena}/` for a standalone case that later promotes by rename into a campaign path. Each tool subfolder appears only when that tool was actually used and something was
saved. A HAR-only case is normal, not a gap, and a manual-only Lightstep or Athena query with nothing worth saving creates no folder.

Every case doc under `investigations/*/docs/` must include an **Inputs used** block stating whether HAR, Lightstep, and Athena were used, and whether each one was saved to disk or used manually only.
That turns a missing saved-data folder into an explicit methodology statement instead of an ambiguous absence.

`investigations/*/docs/<case-id>-*.md` is the mandatory per-case deliverable. `applauseInvestigation/investigations/docs/7231547-android-secure-decoder-failure.md` is the model: it stays bound to one
ticket's household IDs, device IDs, and timeline. `knowledge/<tool>/` is optional, case-independent carry-forward knowledge; the model is
`applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`, rehomed here as a Lightstep note under `knowledge/lightstep/` because the ticket number is not needed to reuse the finding.
Promotion test: if the fact still matters with different household or device IDs, move it to `knowledge/<tool>/`; otherwise it stays in case docs.

Default close-out policy: once a bounded case's docs are written and any reusable findings have been promoted to `knowledge/`, delete its raw `data/.../<case-id>/`. The reference audit already found a
single campaign holding 1.6GB of raw data, so archive-forever does not scale. This default does not apply to a recurring campaign's own `investigation_data` and `investigation_output` tree, which is
governed by that campaign's optional `RETENTION.md`.

For recurring per-date pipelines, split saved files by source or tool provenance, not by an `input/` versus `output/` label. `ctap-smvod-session-report` showed why: manual Lightstep exports and a
later step's own Athena output can both be "inputs" to the next step, but they are different sources and should stay separated as `data/lightstep/` and `data/athena/`.

Use ISO date prefixes for date-keyed artifacts so filenames sort chronologically without extra parsing. Per-date snapshots use `YYYY-MM-DD_<artifact>.csv`; per-range snapshots use
`YYYY-MM-DD_YYYY-MM-DD_<artifact>.csv` with any ticket tag trailing, never inserted between the dates and artifact; cumulative files keep an explicit `_rollup` or existing `_all_dates` suffix because
the date lives in a column, not the filename. This corrects the unsortable `DDMMYYYY` suffix style found in both `ctap-smvod-session-report` and `aws-access-cli`.
