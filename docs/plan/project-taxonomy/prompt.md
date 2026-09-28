# Project taxonomy — prompt

> Classify the kinds of work this project takes on (pipeline, continuous investigation, one-off investigation, tool, experiment), give each a folder skeleton and a submodule-vs-plain-folder rule, and
> write the "start a new investigation" checklist that makes a session search prior art before creating a new top-level folder.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot` (read-only reference — see `README.md`'s mission statement and `CONTEXT.md`'s "Current Constraints") grew eight-plus projects with no shared rule for what kind of
folder a new piece of work becomes. Auditing it (2026-09-28 session) found at least five distinct *shapes* of work living side by side with identical treatment: `aws-access-cli` is a cron-scheduled
Athena reporting pipeline with ~14 scheduled jobs; `ctap-smvod-session-report` and `oasis-athena-mcp` are real git submodules (continuous data-collection project, MCP tool-under-development); `astro-
events-household-report` is also a submodule; `applauseInvestigation` and `mtn-zm-session-device-investigation` are one-off third-party-findings investigations; `vod-asset-ingestion-mapping` and
`vod-playback-timing-probe` are short-lived naming/timing experiments — yet the last five are all plain folders with no distinguishing scaffold, so nothing signals "this is done, archive it" vs "this
is a live pipeline, treat it differently" vs "this is a probe, expect it to be thrown away."

Verified during the same audit: a real git submodule resolves its own `git rev-parse --show-toplevel` to itself, so its own `.github/copilot-instructions.md` (confirmed present on
`ctap-smvod-session-report`) loads independently of the parent workspace's instructions — a plain folder has no such anchor and must borrow the parent's `AGENTS.md`/`CONTEXT.md` instead. That is a
concrete, checkable reason to prefer submodules for anything with its own cadence or instructions, not just a preference.

This story does not touch `github_copilot` (read-only, per `CONTEXT.md`) — it distills the taxonomy `ih-trace-lab` should use going forward, informed by that audit, as the profile of work this project
is meant to re-implement with discipline (see root `README.md`'s mission statement).

`aws-access-cli` additionally has three live system-crontab entries pointing at its scripts (a daily, a weekly, a monthly report job — each hardcoding the `github_copilot/aws-access-cli` path and its
own `.venv`). Crontab is not git-tracked, so no diff/PR review ever sees an edit to it — whenever a pipeline like this eventually gets ported to `ih-trace-lab`, swapping the cron entry to the new path
on the same day the code lands risks a silently broken daily/weekly/monthly report going unnoticed for a full cycle. PT-6 documents the parallel-run-then-flip procedure this migration must follow; it
does not execute any migration now — no pipeline has been ported yet.

A follow-up audit of `applauseInvestigation`'s and `vod-playback-timing-probe`'s own internal folders found a second, systemic problem: both independently wrap their `docs`/`data`/`har` case-artifact
folders inside a subfolder literally named `investigations/` — the same name as this story's own top-level category bucket. Nested (`investigations/<slug>/investigations/{docs,data,har}`), that is the
exact stutter/collision this story must not repeat (**Rule A**, PT-2). Separately, `applauseInvestigation` is not one case — its own `investigations/docs/` already holds nine distinct ticket-prefixed
cases (`7231547`, `7231763`, `7231859`, ...) from one ongoing 3rd-party-testing relationship — it is a **campaign**, not a single bounded investigation, and cases within it are already flat,
ID-prefixed files, not per-case subfolders (**Rule B**, PT-2). `mtn-zm-session-device-investigation`'s own `docs/multi-investigation-config/` shows the same campaign-vs-case tension emerging
organically even in a project classified as a single case.

Separately, comparing actual function bodies (not just names) across `applauseInvestigation/scripts/analyze_har.py`, `vod-playback-timing-probe/scripts/extract_content_ids_from_har.py`, and
`vod-playback-timing-probe/scripts/summarize_har_playbacks.py` found the identical ~5-line "load HAR log.entries" function reimplemented four times (twice within the same project) — proof that "thin,
import `src/lib/*`" is not self-enforcing; a session under time pressure will copy a sibling investigation's script rather than research whether `src/lib/` already covers it. PT-3 extends the existing
`scratch-script-registry` sub-agent-delegated duplicate-check pattern (currently scoped to `scratch/` only) to *any* new script, not just new top-level folders, so reuse is the fast path, not the
disciplined path.

## Scope guard

**In scope:** a taxonomy doc (`docs/guides/project-taxonomy.md`) naming the categories, a per-category folder skeleton applying Rule A (no double `investigations/` wrap) and Rule B (campaign slug,
flat ID-prefixed case files), the submodule-vs-plain-folder decision rule, a canonical target-tree reference (`structure.md`, this story's single source of truth for layout, mirroring
`/Users/abhadra/github_copilot/plan/structure.md`'s own pattern), a "start new work" checklist covering both new top-level folders *and* new scripts inside existing ones (mandatory prior-art search
before either), one lightweight audit script checking existing top-level dirs against the taxonomy, a documented pipeline cron-cutover procedure, `AGENTS.md`/`CONTEXT.md` pointer lines.

**Out of scope:** any change under `/Users/abhadra/github_copilot` (read-only reference, never edited from this project); any actual edit to the live system crontab (PT-6 is a documented procedure for
a *future* pipeline-migration story to follow, not something this story executes); the shared-code module layout that replaces duplicated Athena/CSV/HAR logic, the registry tool that powers the
script-level duplicate-check, and the "shared vs. specific" test for what belongs in `src/lib/` — those are `docs/plan/functional-code-taxonomy/`'s job (FCT-1/FCT-2/FCT-6); this story only decides
*what kind of project* a piece of work is and *where its files sit*, not *what library code it imports* or *how duplication is detected*; converting any existing `ih-trace-lab` folder into a submodule
(no such folders exist yet — this story defines the rule for when a *future* one should be).

## Session-start load hints

- `README.md` — the project mission statement this taxonomy operationalizes.
- `docs/plan/scratch-script-registry/prompt.md` and `stories.md` — the existing sub-agent-delegated duplicate-check pattern (scoped to `scratch/` scripts) this story's PT-3 checklist extends to *any*
  new script, and to new top-level folders; match its delegation style rather than inventing a new pattern.
- `docs/plan/functional-code-taxonomy/prompt.md` — the sibling story this one's PT-2 skeletons must stay compatible with (a pipeline/investigation/tool folder's `scripts/`/`src/` imports that story's
  shared-lib modules; that story's FCT-6 registry is what PT-3's script-level check queries; this story does not re-decide module layout or build the registry itself).
- `structure.md` (this story's own folder) — the canonical target tree; PT-2 edits this file directly, not just prose in the guide doc; read it before PT-2 so the guide doc's skeleton table and this
  file never diverge.
- `docs/guides/git-multi-account-auth.md` — this project's existing precedent for a `docs/guides/*.md` reference doc's tone/structure; match it rather than inventing new formatting conventions.

## Task overview

- **PT-1** — `docs/guides/project-taxonomy.md`: define the five categories (pipeline, continuous investigation, one-off investigation, tool, experiment), one paragraph each, with a `github_copilot`
  example per category from the 2026-09-28 audit.
- **PT-2** — Same doc + `structure.md`: per-category folder skeleton table, Rule A (no double `investigations/` wrap) and Rule B (campaign slug, flat ID-prefixed cases), and the submodule-vs-plain-
  folder decision rule; keeps `structure.md` in sync with the skeleton table in the same commit.
- **PT-3** — Same doc, "Start new work" checklist: category decision tree from PT-1, then a mandatory sub-agent-delegated prior-art search step before *either* creating a new top-level folder *or*
  writing any new script inside an existing one (querying `functional-code-taxonomy`'s FCT-6 registry for the script case).
- **PT-4** — `scripts/dev/check_project_taxonomy.py`: lightweight audit script listing top-level dirs and flagging any without a recognizable category marker, plus tests.
- **PT-5** — `AGENTS.md` + `CONTEXT.md`: one-line pointers to the new guide.
- **PT-6** — Same doc, pipeline cron-cutover procedure: a mandatory parallel-run-then-flip checklist for migrating any live system-crontab entry (e.g. `aws-access-cli`'s three existing cron jobs) to a
  ported pipeline, since crontab edits are not git-tracked and a same-day swap risks a silent broken report going unnoticed for a full cycle.

## Definition of done

- `docs/guides/project-taxonomy.md` exists, covers PT-1/PT-2/PT-3/PT-6 content, and is internally consistent with `structure.md` and with `docs/plan/functional-code-taxonomy/`'s module layout (no
  contradicting folder-skeleton claims across any of the three).
- `structure.md` reflects Rule A and Rule B and is the tree `docs/guides/project-taxonomy.md`'s skeleton table matches exactly.
- `scripts/dev/check_project_taxonomy.py` runs against the current (empty) `ih-trace-lab` tree without error and its tests are green.
- `AGENTS.md` and `CONTEXT.md` each gained exactly one new pointer line; no taxonomy content duplicated into either.
- No file under `/Users/abhadra/github_copilot` was created, edited, or deleted by this story.
- No live system crontab entry is modified by this story — PT-6 only documents the procedure a future pipeline-migration story must follow.

## Perspectives not covered

- This story does not decide *when* an existing `ih-trace-lab` folder should convert from plain-folder to submodule after the fact (only the up-front rule for new work) — that migration decision, if
  it's ever needed, is a follow-up story once a real candidate folder exists, not something to speculatively design now.
