# Reference folder diagrams — prompt

> Extend `scripts/reference_diagram/` and produce one Mermaid diagram set per relevant `github_copilot` reference-repo top-level folder, so `functional-code-taxonomy`, `src-lib-migration`,
> `pipeline-migration`, and `reference-code-gap-migration` sessions have a visual map of what duplicates what, and what each folder should converge to.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A 2026-09-30 session generated `docs/reference-architecture.md` (`scripts/reference_diagram/`) — one flat Mermaid graph of all 13 `github_copilot` top-level project folders with file counts and
(empty, confirmed) cross-project-import edges. A follow-up discussion in the same session concluded that a single flat overview does not carry enough detail to drive the refactor: the
`reference-code-gap-migration` epic already tiers these folders by effort/blocking and has made two concrete new-module promotion decisions (`src/lib/mpd/`, `src/lib/crypto_signing/`), and
`mtn-zm-session-device-investigation` has a real state-machine (`classify_session_outcomes.py`) worth diagramming on its own terms. This story builds the per-folder diagrams that make those decisions
visible and checkable, rather than leaving them as prose in four different plan files.

This is a **documentation/tooling** story — it does not implement any migration itself. It reads the decisions already recorded in `reference-code-gap-migration/README.md` and
`functional-code-taxonomy/` and renders them; it must not re-litigate those decisions.

## Scope guard

**In bounds:** `scripts/reference_diagram/` (extend the existing generator with a per-project flowchart mode), new output files under `docs/reference-diagrams/<project>.md`, one index file linking
them.

**Out of bounds:** `github_copilot` (read-only reference — never write there). Any actual migration code (`src/lib/*`, `src/pipelines/*`, `investigations/*`, `src/tools/*`) — that is
`src-lib-migration`/`pipeline-migration`/`reference-code-gap-migration`'s job, not this story's. Re-deciding the tier list, category assignments, or module-promotion calls already made in
`reference-code-gap-migration/README.md` — flag a disagreement there via that story's own process, do not silently redraw it here.

Does not change runtime behaviour of anything under `src/`; touches only diagram-generation tooling and generated docs.

## Session-start load hints

- `docs/reference-architecture.md` — the existing flat overview this story adds detail beside, not replaces.
- `scripts/reference_diagram/lib.py` / `main.py` / `tests/` — the tool this story extends.
- `docs/plan/reference-code-gap-migration/README.md` — tier list, category corrections, the two module-promotion decisions (`mpd`, `crypto_signing`) that RFD-6/RFD-7 must render faithfully.
- `docs/plan/functional-code-taxonomy/` — target `src/lib/*` module map that convergence diagrams point to.
- `knowledge/vod-asset-ingestion-mapping/` (if present) — source material for RFD-3's hand-authored field-mapping diagram.

## Task overview

- **RFD-1** — Extend the generator with a per-project internal script-dependency flowchart mode.
- **RFD-2** — Tier-1 convergence diagrams (applauseInvestigation, astro-events-household-report, shaka-6001-sa-error-analysis, root `scripts/`).
- **RFD-3** — `vod-asset-ingestion-mapping` hand-authored field/ID-mapping diagram.
- **RFD-4** — `mtn-zm-session-device-investigation` flowchart + outcome-classification state diagram.
- **RFD-5** — `mtn-network-traffic` + root `investigations` flowcharts.
- **RFD-6** — `vod-playback-timing-probe` CLI-chain flowchart + `mpd` convergence diagram.
- **RFD-7** — `smarttv-mtntv` convergence diagram (→ `crypto_signing`).
- **RFD-8** — `aws-access-cli` flowchart + orchestration sequence diagram.
- **RFD-9** — `ctap-smvod-session-report` orchestration sequence diagram + data-flow flowchart.
- **RFD-10** — Index page linking every diagram; note `oasis-athena-mcp`'s deliberate exclusion.

## Definition of done

Every reference-repo top-level folder that is in active migration scope (all except `oasis-athena-mcp`, `config`, `knowledge`, `plan`, `scratch`, `sre` — non-code or already excluded) has at least one
Mermaid diagram under `docs/reference-diagrams/`, each diagram correctly reflects the decisions already recorded in `reference-code-gap-migration` and `functional-code-taxonomy` (no new decisions
invented), the generator additions have tests, and an index page links all of them plus the existing flat overview.

## Perspectives not covered

This story does not validate that the rendered diagrams are *itself* free of drift once the referenced migration stories land and change their target module names — no automated freshness check ties a
diagram to the plan file it renders. A future session updating `reference-code-gap-migration`'s module-promotion table must remember to re-run RFD-6/RFD-7 by hand; nothing here enforces that.
