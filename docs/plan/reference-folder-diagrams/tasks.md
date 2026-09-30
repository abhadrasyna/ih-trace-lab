# Reference folder diagrams — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: none — story complete.**

- [x] **RFD-1** — Extend `scripts/reference_diagram/` with a per-project script-dependency flowchart mode | Owner: AI agent | Model: n/a | Review: `py-code-review` hook | SHA: 02beb49
- [x] **RFD-2** — Tier-1 diagrams: applauseInvestigation, astro-events-household-report, shaka-6001-sa-error-analysis, root `scripts/` | Owner: AI agent | Model: n/a | Review: none | SHA: be1643a
- [x] **RFD-3** — `vod-asset-ingestion-mapping` hand-authored field/ID-mapping diagram | Owner: AI agent | Model: n/a | Review: none | SHA: e8f5616
- [x] **RFD-4** — `mtn-zm-session-device-investigation` flowchart + outcome-classification state diagram | Owner: AI agent | Model: n/a | Review: none | SHA: 93b93c1
- [x] **RFD-5** — `mtn-network-traffic` + root `investigations` flowcharts | Owner: AI agent | Model: n/a | Review: none | SHA: b12c702
- [x] **RFD-6** — `vod-playback-timing-probe` CLI-chain flowchart + `mpd` convergence diagram | Owner: AI agent | Model: n/a | Review: none | SHA: 0be3b4c
- [x] **RFD-7** — `smarttv-mtntv` convergence diagram (→ `crypto_signing`) | Owner: AI agent | Model: n/a | Review: none | SHA: 5cf7a12
- [x] **RFD-8** — `aws-access-cli` flowchart + orchestration sequence diagram | Owner: AI agent | Model: n/a | Review: none | SHA: 9ccd050
- [x] **RFD-9** — `ctap-smvod-session-report` sequence diagram + data-flow flowchart | Owner: AI agent | Model: n/a | Review: none | SHA: ae77a86
- [x] **RFD-10** — Index page linking every diagram; note `oasis-athena-mcp` exclusion | Owner: AI agent | Model: n/a | Review: none | SHA: 79aea36

## Story done when

- **RFD-1** — `scripts/reference_diagram/main.py --project <name>` renders a Mermaid flowchart of that project's internal script-to-script import graph, with tests covering the happy path and a
  project with no internal imports.
- **RFD-2** — `docs/reference-diagrams/{applauseInvestigation,astro-events-household-report,shaka-6001-sa-error-analysis,scripts}.md` each exist, generated via RFD-1's mode, with a short prose note on
  target `src/lib/*` convergence.
- **RFD-3** — `docs/reference-diagrams/vod-asset-ingestion-mapping.md` exists with a field/ID-mapping diagram consistent with `knowledge/vod-asset-ingestion-mapping/` (if harvested) or the project's
  own README.
- **RFD-4** — `docs/reference-diagrams/mtn-zm-session-device-investigation.md` exists with both an auto-generated flowchart and a hand-authored `stateDiagram-v2` for `classify_session_outcomes.py`'s
  outcomes.
- **RFD-5** — `docs/reference-diagrams/{mtn-network-traffic,investigations}.md` exist, generated via RFD-1's mode.
- **RFD-6** — `docs/reference-diagrams/vod-playback-timing-probe.md` exists with a CLI-chain flowchart and a diagram showing DASH-parsing duplication converging into `src/lib/mpd/` per
  `reference-code-gap-migration`'s decision.
- **RFD-7** — `docs/reference-diagrams/smarttv-mtntv.md` exists showing convergence with `investigations/sign_jws_json.py` into `src/lib/crypto_signing/` per `reference-code-gap-migration`'s decision.
- **RFD-8** — `docs/reference-diagrams/aws-access-cli.md` exists with a flowchart (5 report entrypoints → shared executor) and a sequence diagram of `run_daily_reports.py`'s fan-out.
- **RFD-9** — `docs/reference-diagrams/ctap-smvod-session-report.md` exists with a sequence diagram of `run_pipeline.py`'s orchestration and a data-flow flowchart.
- **RFD-10** — `docs/reference-diagrams/README.md` links every diagram above plus `docs/reference-architecture.md`, and states why `oasis-athena-mcp` (superseded by the `athena-mcp-server` submodule)
  has none.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in this file's "Open:" line and add one line to your backlog/session-log file. When the whole story
is done, archive it per this project's own convention — do not leave a done story half-archived.
