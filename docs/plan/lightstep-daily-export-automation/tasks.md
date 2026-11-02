# Lightstep daily export automation — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: LX-6, LX-11, LX-12** (LX-9a to LX-9d, LX-10 and LX-13 are done; they come before the LX-6/LX-7 docs and wrapper; "LX-9" in other text means all four sub-tasks; LX-11 and LX-12 were added
2026-11-02 after the first real daily run and are independent of LX-6).

- [x] **LX-1** — Feasibility spike: reproduce one hand-exported file per kind via the API and diff | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: 00ea164
- [x] **LX-2** — Query templates for the eight exports plus a per-kind registry | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: 1795278
- [x] **LX-3** — Lightstep API client: auth, slicing, truncation-driven auto-split, retries | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 1795278
- [x] **LX-4** — UI-format CSV writer and part-file naming | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: ea2f728
- [x] **LX-5** — `export_lightstep_day.py` CLI for all eight kinds, with input check | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: eb2e43e
- [x] **LX-8** — SOLID refactor of the export CLI per `docs/refactor` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 661b424
- [x] **LX-9a** — Pure part-series stitch module and part-file reader | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: d87c17c
- [x] **LX-9b** — Runner writes part files with a manifest, verified resume, `--fresh`, `--part-hours` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: c9c0920
- [x] **LX-9c** — Stitch per kind, `smvod-ts` from stitched parts, pre-cleanup sanity check and cleanup | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 96f58f1
- [x] **LX-9d** — Per-step logging with ETA and opt-in per-date log files pruned after 7 days | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 850d079
- [x] **LX-10** — Parallel fetch of part windows with bounded workers, FCID kept in worker threads | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: cbcff3d
- [ ] **LX-6** — Docs, `SCRIPTS.md` entry and parity run against a hand-exported day | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [x] **LX-7** — Cron-ready wrapper: export, input check, pipeline, error report, household ranking | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: pending
- [x] **LX-13** — Past-month debug table: shared `--table-suffix`, plus `--force`, through the pipeline and the daily wrapper | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: 3690f57
- [ ] **LX-11** — Daily wrapper streams each step's output live and logs a heartbeat for quiet steps | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-12** — Per-script dated log files under `investigations/ctap-smvod/logs/` by default | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-14** — Daily wrapper derives `--table-suffix` for a past-month day (or fails fast) instead of only warning | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-15** — Tenant-aware `smvod-ts` coverage check (low-volume tolerance) and check-inputs legend matches real blocking behaviour | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **LX-16** — Export skips an existing kind quietly, without the per-part "missing or failed verification" sanity warnings | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **LX-17** — Daily wrapper resume hint re-runs only failed tenants, steps use one pinned interpreter, and the check-inputs legend is logged once | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer | SHA: —
- [ ] **LX-18** — Daily pipeline health check: parse the run summary and alert on FAILED/NOT RUN steps or a missing run, with a warning digest | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —

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
- **LX-13** — `--table-suffix` (e.g. `oct26`) selects `<id>_ccl_debug_events_<suffix>` through one shared helper, reaches only Steps 4 and 6f of `run_pipeline.py` and the `run_pipeline` step of the
  daily wrapper, `--force` re-pulls over stale CSVs, and a past-month day run without a suffix logs a warning.
- **LX-11** — a step's lines appear in the wrapper log as the step prints them (not after it exits), a step silent for 60 s logs a heartbeat, and the timeout still kills the whole process group
  (exit 124) with the same captured output as before.
- **LX-12** — every `ctap-smvod` script writes `<investigation>/logs/<prefix>_<date>.log` by default through one wrapper, with no per-script path, and old files of the same prefix are pruned.
- **LX-14** — a run for a day outside the current UTC month never reads the unsuffixed debug table silently: the suffix (e.g. `oct26`) is derived and passed to `run_pipeline`, or the run stops with a
  clear error. Found in the 2026-10-31 log, where the unsuffixed run gave 5 GH 1xxx rows against 177 after the `--table-suffix oct26 --force` rerun.
- **LX-15** — a quiet tenant (e.g. ZM, 133 sessions, first span 04:17 UTC) no longer fails the export and the input check on `smvod-ts` coverage, and the legend states whether a FAIL blocks the
  pipeline.
- **LX-16** — re-running over an existing `smvod-release` file logs one skip line and no 24 per-part verification warnings, and keeps no stale temp parts.
- **LX-17** — the printed resume command names the failed tenants (`--tenants`), every step uses the same interpreter (the repo `.venv`), and the check-inputs table and legend appear once per run.
- **LX-18** — a failed or not-run step, or a missing/incomplete daily log, raises one notification (tenant, step, FCID) through a pluggable notifier; warnings appear only in a digest line; the same
  run is never alerted twice; verified on the 30/31 Oct logs.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
