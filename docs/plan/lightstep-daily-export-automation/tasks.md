# Lightstep daily export automation — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: LX-9a, LX-9b, LX-9c, LX-9d, LX-10, LX-6, LX-7** (do LX-9a to LX-9d, then LX-10, before the LX-6/LX-7 docs and wrapper; "LX-9" in other text means all four sub-tasks).

- [x] **LX-1** — Feasibility spike: reproduce one hand-exported file per kind via the API and diff | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: 00ea164
- [x] **LX-2** — Query templates for the eight exports plus a per-kind registry | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: 1795278
- [x] **LX-3** — Lightstep API client: auth, slicing, truncation-driven auto-split, retries | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 1795278
- [x] **LX-4** — UI-format CSV writer and part-file naming | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: ea2f728
- [x] **LX-5** — `export_lightstep_day.py` CLI for all eight kinds, with input check | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: eb2e43e
- [x] **LX-8** — SOLID refactor of the export CLI per `docs/refactor` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 661b424
- [ ] **LX-9a** — Pure part-series stitch module and part-file reader | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-9b** — Runner writes part files with a manifest, verified resume, `--fresh`, `--part-hours` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-9c** — Stitch per kind, `smvod-ts` from stitched parts, pre-cleanup sanity check and cleanup | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-9d** — Per-step logging with ETA and opt-in per-date log files pruned after 7 days | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-10** — Parallel fetch of part windows with bounded workers, FCID kept in worker threads | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-6** — Docs, `SCRIPTS.md` entry and parity run against a hand-exported day | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **LX-7** — Cron-ready wrapper: export, input check, pipeline, error report, household ranking | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —

## Story done when

- **LX-1** — one export per kind was reproduced through the API and the differences from the hand export are written down, with go/no-go per kind.
- **LX-2** — every kind has a parameterised template in `queries/lightstep/` and a registry entry naming project, region, tenant system and output file name.
- **LX-3** — the client returns every series for a window by splitting any slice that hits the 50-series cap, and never reads the token from anywhere but the environment.
- **LX-4** — written files match the UI export format in structure (BOM, quoting, header) and use the existing `_NN_` part naming.
- **LX-5** — one command produces all eight files for a tenant and UTC date, supports `--kinds` and `--tenant`, and fails loudly on truncation, empty results or a failed input check.
- **LX-8** — the CLI is orchestration only, every SOLID finding from the LX-5 review is fixed, and behaviour and tests are unchanged.
- **LX-9a** — merging part series gives the same rows and recomputed `min/max/avg/sum` as a one-shot fetch, and a written part file reads back to the same rows.
- **LX-9b** — parts are written as they are fetched with a manifest, a rerun fetches only missing or invalid windows, and `--fresh` ignores all parts.
- **LX-9c** — stitched files equal the one-shot output, `smvod-ts` is derived from the stitched `smvod` parts, and the temp subfolder is removed only after every sanity check passes.
- **LX-9d** — logs show one INFO line per step under one FCID with an ETA, and the per-date log file is written and pruned after 7 days without touching other files.
- **LX-10** — windows are fetched by a bounded worker pool behind an injected runner, output equals the `--workers 1` run, worker log lines keep the FCID, and a failure keeps finished parts.
- **LX-6** — usage docs and the `SCRIPTS.md` registry are updated, and a key-set parity run for a ZA day within the 7-day retention window is documented.
- **LX-7** — one command runs the whole daily chain for a UTC date, logs every step under one FCID, verifies the output CSVs and exits non-zero on failure.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
