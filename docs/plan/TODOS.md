# `docs/plan/` — story/epic completion order

> Derived from each story/epic's own stated blocking dependencies (its `README.md`/`prompt.md`/`tasks.md`), not re-decided here. Regenerate this section by re-reading those files if any story's
> dependencies change — this is a snapshot, not a second source of truth.

## Phase 0 — Foundation (no blocking dependencies, parallelizable)

- [x] `tenant-registry` — canonical MTN tenant config + resolver. Unblocks `query-catalog` QC-4's live tenant resolution dependency.
  - 2026-09-30: TR-1 landed in `2140cc8`; the scratch probe recorded dedicated vs shared Lightstep resolution and the human-confirmed MCP results.
  - 2026-09-30: TR-2 landed in `78880e5`; `config/tenants.yaml` is now the canonical MTN tenant registry for the four confirmed opcos.
  - 2026-09-30: TR-3 landed in `7ad3b7d`; `src/tenant_registry/` now loads YAML-backed tenant configs and builds per-system query contexts.
  - 2026-09-30: TR-4 landed in `77a6e79`; `scripts/resolve_tenant.py` now resolves any known id to Lightstep, Matisse, or Athena JSON context.
  - 2026-09-30: TR-5 landed in `14aa88b`; the CLI-first tenant-resolution protocol is now documented and enforced from `AGENTS.md`.
  - 2026-09-30: TR-6 landed in `ea62e1e`; pytest now covers registry lookup, shared-project guards, query targets, and the CLI.
- [x] `project-taxonomy` — category definitions, folder skeletons, `config/data_paths.yaml`. Blocks `pipeline-migration` (PT-1/2/6/7).
  - 2026-09-30: PT-1 through PT-8 landed (`5e2abfd`..`e3fa1e2`, bookkeeping `5147979`), merged to `main` in `299e8a4`.
- [ ] `functional-code-taxonomy` — `src/lib/*` module map + `Protocol` skeletons. Blocks `src-lib-migration` (FCT-1/2/7).
- [x] `scratch-script-registry` — `SCRIPTS.md` generator + promotion CLI. Complete through SSR-7; no dependents among the stories below; independent.
  - 2026-09-30: SSR-1 landed in `e564794`; root `SCRIPTS.md` remains intentionally deferred to SSR-7.
  - 2026-09-30: SSR-2 landed in `501f818`; manual promotion and age-based candidate listing now exist.
  - 2026-09-30: SSR-3 landed in `ca5c1b6`; `scratch/SCRATCH.md` now requires the delegated duplicate-check workflow and documents the registry/promotion commands.
  - 2026-09-30: SSR-4 landed in `615998a`; pytest now covers both registry/promotion CLIs, with package markers added for `tests/` and `tests/dev/`.
  - 2026-09-30: SSR-5 landed in `97278de`; `AGENTS.md` now carries the single pointer back to `scratch/SCRATCH.md`'s registry section.
  - 2026-09-30: SSR-6 landed in `ea76445`; the repo-local `session-close` override now conditionally regenerates `SCRIPTS.md`.
  - 2026-09-30: SSR-7 landed in `622dfdf`; root `SCRIPTS.md` is now committed, closing the story.
- [ ] `reference-knowledge-harvest` — ongoing docs-only harvest from `github_copilot`. No dependents among the stories below; independent, can run indefinitely in parallel.

## Phase 1 — Query catalog

- [ ] `query-catalog` — QC-1/2/3/5/6 have no dependency; QC-4's former `tenant-registry` blocker is now satisfied.

## Phase 2 — Reference diagrams (of the *original* `github_copilot` code)

- [ ] `reference-folder-diagrams` — needs `reference-code-gap-migration`'s GAP-1 decisions (already closed — `mpd`/`crypto_signing` promotion calls exist) to cite in RFD-6/RFD-7. Produces
      `docs/reference-diagrams/*.md`, read-only-reference-only, no migration code touched. Best done early so its diagrams can *inform* the migration epics below, not just document them after the
      fact.

## Phase 3 — Src-lib migration (real implementations)

- [ ] `src-lib-migration` epic — blocked on `functional-code-taxonomy` FCT-1 (module map), FCT-2 (`athena`/`report_render`/`har` Protocols), FCT-7 (`PathResolver`). Six stories inside land in any
      order once unblocked, except `auth-lib-migration` additionally depends on `athena-lib-integration` (reuses its `sso_auth` shape).

## Phase 4 — Pipeline migration

- [ ] `pipeline-migration` epic — blocked on `project-taxonomy` PT-1/2/6/7, all of `src-lib-migration`, and `query-catalog`. Two stories (`aws-access-cli-pipeline-migration`,
      `ctap-smvod-investigation-migration`) land in any order relative to each other once unblocked.

## Phase 5 — Reference code gap migration (remaining 10 `github_copilot` projects)

- [ ] `reference-code-gap-migration` epic — Tier 1 (`applause-investigation-migration`, `astro-events-household-investigation-migration`, `shaka-6001-sa-investigation-migration`,
      `root-scripts-tool-migration`) ready as soon as `src-lib-migration` lands. Tier 2 (`vod-asset-ingestion-investigation-migration`, `mtn-zm-device-investigation-migration`,
      `mtn-network-traffic-tool-migration`, `root-investigations-migration`) additionally needs `project-taxonomy` PT-1/2/7. Tier 3 (`vod-playback-timing-probe-tool-migration`,
      `smarttv-mtntv-tool-migration`) is blocked until `src/lib/mpd/` and `src/lib/crypto_signing/` exist — these are new modules promoted by this epic's own GAP-1 decision but **built by
      `src-lib-migration`**, so `src-lib-migration`'s `README.md`/`stories.md` need a follow-up edit adding those two modules before Tier 3 can start (see this epic's own "Supersession/coordination"
      note — not yet done as of this writing).

## Phase 6 — Verification: diagram-vs-implementation diff (not yet its own story)

Goal: for every python refactor under `src-lib-migration` and `reference-code-gap-migration`, compare the *original* `github_copilot` diagrams (Phase 2 output) against the *migrated* code, to catch
logic silently dropped or altered during the port — a systematic check, not manual re-reading of both codebases.

No existing story owns this — `reference-folder-diagrams` is explicitly scoped "docs/tooling only" against the read-only reference, and does not re-diagram `ih-trace-lab`'s own new code. Proposed
follow-up story (create via `_TEMPLATE` once Phase 3/5 stories start landing):

1. Extend `scripts/reference_diagram/` (already built by RFD-1) with a second mode pointed at `ih-trace-lab`'s own `src/lib/*` / `investigations/*/scripts` / `src/pipelines/*`, producing the same
   Mermaid flowchart/sequence-diagram shape as the Phase 2 output, so both sides are directly comparable.
2. Add a single-responsibility script (e.g. `scripts/dev/diff_reference_diagrams.py`, registered in `SCRIPTS.md` per `scratch-script-registry`'s convention) that parses both Mermaid graphs' node and
   edge lists and reports the set difference — nodes/flows present in the original with no corresponding node in the migrated code — rather than relying on eyeballing two diagrams side by side.
3. Run this diff per migrated project as each `src-lib-migration`/`reference-code-gap-migration` sub-story lands, not as one big pass at the very end — catches gaps while the context of that specific
   port is still fresh.
4. Any finding becomes either a fix to the just-landed migration story (if genuinely missed logic) or a documented, deliberate scope exclusion (if the original node was dead code / out of scope) —
   never left as a silent, unexplained diagram mismatch.

## Notes

- `_TEMPLATE` excluded (not a real story). Ordering above still routes through `reference-code-gap-migration` and `reference-folder-diagrams` even though the originating review excluded them from deep
  review, because Phase 6 (explicitly requested) needs both.
- Model: all tasks across every story currently specify `claude-sonnet-5`. Kept as the default here; escalate per-task to a stronger model only if a specific port's first-pass output needs a redo, not
  as a blanket change.
