# Reference code gap migration — prompt

> Plan (and later port) the ~166 `.py` files across 10 `github_copilot` reference projects that neither `pipeline-migration` nor `src-lib-migration` currently cover — resuming a 2026-09-30 audit
> session, not yet started.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A 2026-09-30 session asked whether `docs/plan/pipeline-migration/` and `docs/plan/src-lib-migration/` together plan for *all* Python code migration out of `/Users/abhadra/github_copilot` (read-only
reference). They do not: `pipeline-migration` only fully ports `aws-access-cli` and `ctap-smvod-session-report`; `src-lib-migration` only extracts shared domain-mechanism patterns (auth, athena,
csv_io, report_render, har, curl_to_python, paths) from a handful of other projects as *citation sources*, never porting their actual business logic. Ten projects have zero migration plan:
`vod-playback-timing-probe` (65 files), `mtn-zm-session-device-investigation` (32), `mtn-network-traffic` (22), `vod-asset-ingestion-mapping` (15), root `investigations/` (10), `applauseInvestigation`
(9), `shaka-6001-sa-error-analysis` (6), root `scripts/` (4), `astro-events-household-report` (2), `smarttv-mtntv` (1). `oasis-athena-mcp` (34 files) was checked and confirmed **not** a gap — it's
superseded by the already-independent `athena-mcp-server` submodule that `athena-lib-integration` wires in.

A same-session background audit (`explore` agent, 2026-09-30) did a file-by-file classification of all 166 files against the "shared vs. specific" test and the 7 planned `src/lib/*` modules. Full
findings are in this story's `spec.md` — read it before scoping any task below. This `prompt.md` only session-start-instructs and index-points; it does not restate the audit.

## Scope guard

- This story does **not** re-decide `project-taxonomy`'s category definitions or `src-lib-migration`'s existing 7-module design — it consumes both as-is, the same way `pipeline-migration` does.
- This story does **not** touch `oasis-athena-mcp` — confirmed superseded, not a gap, no task here should re-open it.
- No file under `/Users/abhadra/github_copilot` is ever created, edited, or deleted — read-only reference throughout, per `CONTEXT.md`'s constraint.
- Whether this becomes one epic (10 stories, mirroring `pipeline-migration`'s shape) or several independently-landing stories (e.g. cheap wins first: `applauseInvestigation`,
  `astro-events-household-report`; defer the two 60+/30+-file projects) is an **open decision**, not yet made — see "Task overview" below, GAP-1 is that decision, not a foregone one.

## Session-start load hints

- `spec.md` (this story's own file) — the full 10-project, file-by-file audit table; read before GAP-1.
- `docs/plan/pipeline-migration/README.md` — the shape this story's eventual epic (if chosen) should mirror: one epic, N stories, shared blocking-dependency list, lib-vs-script split test cited per
  file.
- `docs/plan/src-lib-migration/README.md` — the 7 planned modules and existing citation list; GAP-1 must reconcile new duplication clusters `spec.md` found against this list without re-deciding module
  boundaries already settled there.
- `docs/plan/project-taxonomy/structure.md` — worked-example categories already named for 4 of the 10 projects (`applauseInvestigation` → `investigations/applause/`,
  `mtn-zm-session-device-investigation` → `investigations/mtn-zm-device/`, `vod-asset-ingestion-mapping` and `vod-playback-timing-probe` → `experiments/`). **Known conflict, unresolved:** the
  2026-09-30 audit suggests `vod-asset-ingestion-mapping` reads as a recurring-campaign *investigation* (its own README calls it "a continuous data-gathering exercise"), not an experiment. GAP-1 must
  resolve this — either accept `structure.md`'s categorization as-is with a documented reason, or flag it back to `project-taxonomy` for a `structure.md` correction. Do not silently pick one.

## Task overview

- **GAP-1** — Decide the scope shape (one epic w/ 10 stories vs. split by size/priority) and resolve the `vod-asset-ingestion-mapping`/`vod-playback-timing-probe` category conflict with
  `structure.md`. Not yet started — this is the first unchecked task; see `tasks.md`.
- Further tasks (one per chosen project/story) are deliberately not yet written — they depend on GAP-1's decision. Do not add them before GAP-1 lands.

## Definition of done

- GAP-1 decided and recorded (epic shape + category-conflict resolution), with the resulting story/epic skeleton created (mirroring `pipeline-migration`'s file set) and this story's own `tasks.md`
  updated to either point at the new epic/story location (if this folder is superseded) or continue with per-project tasks (if kept flat).

## Perspectives not covered

- `spec.md`'s "new shared module" candidates (`mpd`/DASH parser, playback-session/timing correlator, network-diagnostics, ADI/XML+asset-identity mapper, device/user-agent identity, crypto/JWS signing)
  are named but not scoped as their own stories — GAP-1 should decide whether any of these get promoted to an 8th+ `src/lib/*` module or stay project-local duplication accepted as a known cost. Not
  decided in this session.
