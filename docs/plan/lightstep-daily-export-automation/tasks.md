# Lightstep daily export automation — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: LX-2, LX-3, LX-4, LX-5, LX-6, LX-7.**

- [x] **LX-1** — Feasibility spike: reproduce one hand-exported file per kind via the API and diff | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: 00ea164
- [ ] **LX-2** — Query templates for the eight exports plus a per-kind registry | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **LX-3** — Lightstep API client: auth, slicing, truncation-driven auto-split, retries | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-4** — UI-format CSV writer and part-file naming | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-5** — `export_lightstep_day.py` CLI for all eight kinds, with input check | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-6** — Docs, `SCRIPTS.md` entry and parity run against a hand-exported day | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **LX-7** — Cron-ready wrapper: export, input check, pipeline, error report, household ranking | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —

## Story done when

- **LX-1** — one export per kind was reproduced through the API and the differences from the hand export are written down, with go/no-go per kind.
- **LX-2** — every kind has a parameterised template in `queries/lightstep/` and a registry entry naming project, region, tenant system and output file name.
- **LX-3** — the client returns every series for a window by splitting any slice that hits the 50-series cap, and never reads the token from anywhere but the environment.
- **LX-4** — written files match the UI export format in structure (BOM, quoting, header) and use the existing `_NN_` part naming.
- **LX-5** — one command produces all eight files for a tenant and UTC date, supports `--kinds` and `--tenant`, and fails loudly on truncation, empty results or a failed input check.
- **LX-6** — usage docs and the `SCRIPTS.md` registry are updated, and a key-set parity run for a ZA day within the 7-day retention window is documented.
- **LX-7** — one command runs the whole daily chain for a UTC date, logs every step under one FCID, verifies the output CSVs and exits non-zero on failure.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
