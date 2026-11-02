# Lightstep daily export automation — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open, in this order: LX-6a, LX-14, LX-15, LX-16, LX-19, LX-17, LX-11, LX-20, LX-22, LX-24, LX-25, LX-26, LX-23, LX-27, LX-12, LX-18, LX-6b, LX-21** (reordered 2026-11-02 for resilience then
maintainability: the time-boxed parity run first, silent-wrong-data and false-failure fixes next, the wrapper step-identity refactor LX-19 before the tasks that touch the same code (LX-17, LX-11),
then the call and data optimisations LX-24 to LX-27 once the shared runner exists, the mechanical 60-file LX-12 and the health check LX-18 after the wrapper and its log layout settle, docs last; LX-6
was split into 6a/6b; LX-19 to LX-22 came from the `run_daily_pipeline.py` and SOLID/pattern reviews and LX-23 to LX-27 from the data/output and Lightstep/Athena call reviews). LX-9a to LX-9d count as
"LX-9" in other text; LX-21 is optional and needs LX-24. **Shared runtime (2026-11-02):** the generic runner, run summary/status file, SSO pre-flight, pool, prune and health-check core are built once
in `docs/plan/shared-pipeline-runtime/` (SPR-1 to SPR-6), shared with the aws-access-cli hardening story. LX-19 needs SPR-2, LX-12 needs SPR-2, LX-24 needs SPR-3, LX-21 needs SPR-4, LX-27 needs SPR-5,
LX-18 needs SPR-6; do SPR-1 and SPR-2 alongside LX-6a/LX-14/LX-15/LX-16, and if the first unchecked task is blocked on an SPR task, do the next unblocked one and say so.

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
- [x] **LX-7** — Cron-ready wrapper: export, input check, pipeline, error report, household ranking | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: pending
- [x] **LX-13** — Past-month debug table: shared `--table-suffix`, plus `--force`, through the pipeline and the daily wrapper | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: 3690f57
- [ ] **LX-6a** — Parity run of the daily export against a hand-exported ZA day (time-boxed: the 29 Oct hand export leaves the 7-day retention window about 5 Nov) | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **LX-14** — Daily wrapper derives `--table-suffix` for a past-month day (or fails fast) instead of only warning | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-15** — Tenant-aware `smvod-ts` coverage check (low-volume tolerance) and check-inputs legend matches real blocking behaviour | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **LX-16** — Export skips an existing kind quietly, without the per-part "missing or failed verification" sanity warnings | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **LX-19** — (needs SPR-2) Daily wrapper step identity: `Step.id`/`group`/`tenant`, resume flags derived from the parsed args, plan/runner/summary split into `scripts/lib/` modules behind a
  `Protocol` (design review first) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-17** — Daily wrapper resume hint re-runs only failed tenants, steps use one pinned interpreter, and the check-inputs legend is logged once | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer | SHA: —
- [ ] **LX-11** — Daily wrapper streams each step's output live and logs a heartbeat for quiet steps | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-20** — Daily wrapper: drop the duplicate 1xxx extract if `run_pipeline` Step 6e already produces it, and isolate a failed tenant so the others still complete | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-22** — (needs SPR-2) `run_pipeline.py` adopts the shared step runner and a typed step table (one runner for both scripts, steps no longer positional tuples) | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-24** — (needs SPR-3) One run-level SSO pre-flight (children skip their own) and DRM exports gated by `--skip-drm-reports` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **LX-25** — Adaptive Lightstep window sizing from the previous run's call and truncation counts, and an up-front skip of finished days | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **LX-26** — Spike: one shared Lightstep fetch for ZM and GH (same project), split locally by `busUnitId` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **LX-23** — One Athena debug-events extract per tenant-day shared by Steps 4 and 6f (and the investigation scripts), plus one combined sessions query | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-27** — (needs SPR-5) Artifact registry (producer, readers, retention) and a dry-run-first prune script for `data/` and `output/` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **LX-12** — (needs SPR-2) Per-script dated log files under `investigations/ctap-smvod/logs/` by default | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-18** — (needs SPR-6) Daily pipeline health check: parse the run summary and alert on FAILED/NOT RUN steps or a missing run, with a warning digest | Owner: Copilot CLI | Model:
  claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LX-6b** — Docs and `SCRIPTS.md` entries for the export command, the daily wrapper and the health check, plus the recorded LX-6a parity result | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: user | SHA: —
- [ ] **LX-21** — (optional, needs SPR-4) Run per-tenant chains in parallel with bounded workers and an Athena concurrency cap | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —

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
- **LX-6a** — a key-set parity run of the daily export for a ZA day still inside the 7-day retention window is recorded (tolerance about 3 %, known differences listed) before the hand export expires.
- **LX-6b** — `usage.md`, `lightstep-drm-exports.md`, `SCRIPTS.md` and `CONTEXT.md` describe the export command, the daily wrapper and the health check, and cite the LX-6a result (token setup, 7-day
  retention and measured rate limits included).
- **LX-7** — one command runs the whole daily chain for a UTC date, logs every step under one FCID, verifies the output CSVs and exits non-zero on failure.
- **LX-13** — `--table-suffix` (e.g. `oct26`) selects `<id>_ccl_debug_events_<suffix>` through one shared helper, reaches only Steps 4 and 6f of `run_pipeline.py` and the `run_pipeline` step of the
  daily wrapper, `--force` re-pulls over stale CSVs, and a past-month day run without a suffix logs a warning.
- **LX-11** — a step's lines appear in the wrapper log as the step prints them (not after it exits), a step silent for 60 s logs a heartbeat, and the timeout still kills the whole process group
  (exit 124) with the same captured output as before.
- **LX-12** — every `ctap-smvod` script writes `<investigation>/logs/<prefix>_<date>.log` by default through one wrapper, with no per-script path, old files of the same prefix are pruned after the
  shared 7-day default (`DEFAULT_LOG_KEEP_DAYS`).
- **LX-14** — a run for a day outside the current UTC month never reads the unsuffixed debug table silently: the suffix (e.g. `oct26`) is derived and passed to `run_pipeline`, or the run stops with a
  clear error. Found in the 2026-10-31 log, where the unsuffixed run gave 5 GH 1xxx rows against 177 after the `--table-suffix oct26 --force` rerun.
- **LX-15** — a quiet tenant (e.g. ZM, 133 sessions, first span 04:17 UTC) no longer fails the export and the input check on `smvod-ts` coverage, and the legend states whether a FAIL blocks the
  pipeline.
- **LX-16** — re-running over an existing `smvod-release` file logs one skip line and no 24 per-part verification warnings, and keeps no stale temp parts.
- **LX-17** — the printed resume command names the failed tenants (`--tenants`), every step uses the same interpreter (the repo `.venv`), and the check-inputs table and legend appear once per run.
- **LX-18** — a failed or not-run step, or a missing/incomplete daily log, raises one notification (tenant, step, FCID) through a pluggable notifier; warnings appear only in a digest line; the same
  run is never alerted twice; verified on the 30/31 Oct logs.
- **LX-19** — `run_daily_pipeline.py` is orchestration only: steps carry `id`/`group`/`tenant`, `--from-step` and the printed resume command come from the same parsed args (no name-prefix matching),
  and the planner, runner and summary are separate `scripts/lib/` modules with the runner injected as a `Protocol`; behaviour and the existing tests are unchanged.
- **LX-20** — the 1xxx report is produced once per run (or the second extract is justified in writing), and a failed tenant no longer stops the other tenants' steps; the summary and exit code still
  report it.
- **LX-22** — `run_pipeline.py` has no direct `subprocess.run` loop: it runs its steps through the shared runner from LX-19 (injected, so its tenant loop is testable offline), its steps are typed
  `Step` entries, Step 1b's post-check is tied to a step id and not a list position, and its output, skip flags and exit codes are unchanged.
- **LX-24** — `run_pipeline.py` and the wrapper refresh the SSO session once per run and pass `--skip-auth-check` to every Athena child, and a run with `--skip-drm-reports` makes no mDRM/CDM/LRM
  Lightstep exports.
- **LX-25** — the exporter records calls and truncated windows per tenant, kind and day, starts the next day with window sizes derived from them, makes fewer calls than the fixed-window run for the
  same output (compared in a recorded run), and finished days are skipped before any API call.
- **LX-26** — a written go/no-go for fetching ZM and GH in one Lightstep query, with call counts and a key-set comparison against the per-tenant exports; implemented only if the go criteria hold.
- **LX-23** — Steps 4 and 6f read one cached debug-events extract per tenant and day instead of querying `ccl_debug_events` each, Step 3 and the ingest export share one `unified_sessions` query, the
  outputs match the old ones, and a recorded run shows fewer Athena queries.
- **LX-27** — every artifact under `data/` and `output/` has a registry row (producer, readers, retention), unused or duplicate artifacts are listed, and the prune script defaults to a dry run and
  deletes only registry-approved files older than their retention.
- **LX-21** — with `--parallel-tenants N`, per-tenant chains run concurrently with the same results as the serial run, Athena-using steps are capped, one tenant's failure leaves the others complete,
  and every log line keeps the FCID and a tenant prefix.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
