# Household usage tracking — prompt

> A daily, config-driven report of sm-vod/CTAP playback usage per tracked household and device (per-household tenant, ZA for now), built from Athena and Lightstep, written to
> `output/reports/usage/<TENANT>/YYYY-MM-DD.md`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The team shares two household ids (HHIDs) for testing on tenant ZA: one with four named people (each a device id) that will gain a fifth, and a second with four more. Today there is no single place to
see who actually played what, whether playback errored, and whether Athena and Lightstep agree. A daily report, driven by a roster file the team edits, answers that without anyone running queries by
hand. Some HHIDs in the roster must be listed but not tracked, and any new device appearing on a tracked HHID must be flagged so it can be added to the roster.

Prior art found while scoping (2026-11-04), not to be rebuilt: `queries/athena/ctap-smvod-household-unified-sessions.sql` (sessions per household),
`queries/lightstep/smvod-session-inventory-by-device.md` (sm-vod sessions per device), `queries/athena/e6auj7k7-ccl-debug-events-clientid-datetime.sql` (error detail by `clientid`),
`src/pipelines/aws_access_cli/runtime.py` (`make_auth`, `make_athena_client`, `RuntimeConfig`), `scripts/lib/lightstep_api.py` (token loading, `query_timeseries`, slicing) and `config/tenants.yaml`
(ZA ids, profile, region).

## Decisions already made (2026-11-04, with the user)

- Tenant: a required `tenant` on each roster household, resolved through `config/tenants.yaml`, never hardcoded; only ZA is populated for now, and one report is written per tenant.
- Scope: playback only (sm-vod and CTAP). Navigation events are out.
- Content name comes from `unified_sessions`; error code and message come from `<tenant>_ccl_debug_events`, and only for sessions or devices that errored.
- Output: a Markdown file only, one per tenant (`output/reports/usage/<TENANT>/YYYY-MM-DD.md`). No email or chat delivery.
- Roster: `config/tracked_households.yaml` is committed. Each household has `track: true|false`; only tracked ones are queried or reported.
- Any device on a tracked HHID that is not in its `members` list is flagged in the report's Anomalies section.
- Data source (2026-11-04): local-first. The report reads the ctap-smvod pipeline's local exports (`investigations/ctap-smvod/data/lightstep/ZA/<date>_smvod.csv` and
  `data/athena/ZA/<date>_session.csv`, `_error_eventdata.csv`); the cron runs after those downloads. A missing local file fails loudly, never a silent zero. `--live-athena` and `--live-lightstep`
  switch that source to a live query. The 5xx column is dropped (the sm-vod export has no status code); errors come from Athena playback outcome and the debug-events table.
- Cron already exists for the other pipelines (`$PY -m ... >> $LOGS/cron_*.out`); this story adds one more job line in that style. The user installs it; the repo documents the line.

## Open decisions (resolve in UT-1 before any code)

- **Default report date offset.** Local-first means the date must be one the download pipeline has already produced (it runs for D-2 at 13:00). UT-1 confirms the Athena export's lag (the newest local
  Athena file on 2026-11-04 was 2026-10-31, older than the Lightstep one) and sets the default `--date` offset and cron time; `--live-*` is for fresher dates.
- **Where the shared Athena factories live.** `make_auth` and `make_athena_client` sit in `src/pipelines/aws_access_cli/runtime.py`. Importing them from a second pipeline creates a
  pipeline-to-pipeline dependency; the alternative is extracting them into `src/lib`. UT-1 decides, and records it.

## Scope guard

In bounds: a new pipeline package `src/pipelines/usage_tracking/` (its `scripts/`, `tests/`, `README.md`), `config/tracked_households.yaml`, new query files under `queries/athena/` and
`queries/lightstep/` with their index entries, `output/reports/usage/` output, `SCRIPTS.md`, and the "What Exists" section of `CONTEXT.md`.

Out of bounds: changing any existing pipeline's behaviour (`aws_access_cli`, `ctap-smvod`, the Lightstep export), the shared-pipeline-runtime story's code, populating tenants other than ZA (the roster
and sources are per-tenant, so adding one is a config change only), non-playback events, report delivery, and installing the cron entry. If UT-1 chooses to extract the Athena factories into `src/lib`,
that extraction is its own follow-up task and must leave `aws_access_cli` behaviour unchanged.

Runtime impact: a new read-only job; it only reads Athena and Lightstep and writes under `output/reports/usage/` and `logs/`. Secrets stay in the gitignored `.env`; HHIDs and device ids are
identifiers, not secrets, and are committed by decision.

## Session-start load hints

- `docs/refactor/design-principles.md`, `docs/refactor/code-review-checklist.md`, `docs/refactor/logging-and-correlation-id.md` — the design rules this story is held to (see "Design rules applied").
- `docs/guides/project-taxonomy.md` — this is a Pipeline: `scripts/`, `tests/`, `README.md` documenting the schedule.
- `docs/guides/tenant-resolution.md` and `docs/guides/query-catalog.md` — resolve tenant ids through `scripts/resolve_tenant.py`; new queries go in the catalog, not inside Python.
- `knowledge/mtn-sa-athena-bridge-keys-and-gotchas.md` — always scope by household id and device id together; `unified_sessions` uses `user_id` for the household and `device_id` for the device.
- `knowledge/mtn-athena-unified_e6auj7k7-tables.md` — `ccl_debug_events` columns, the `clientid` = `<deviceId>:<householdId>` convention, and the monthly-table naming for older months.
- `docs/plan/shared-pipeline-runtime/` — a sibling story (run summary, SSO pre-flight, bounded pool). Reuse its pieces if they have landed; do not rebuild them here.

## Design rules applied (from `docs/refactor/`)

- **DIP and testability:** every external system (Athena, Lightstep, clock, filesystem) is injected; no module builds its own client. Tests use fakes and never touch the network.
- **Protocol over ABC:** the data sources are `typing.Protocol` seams (`SessionSource`, `RequestSource`); a plain function is preferred over a class where no state is carried.
- **OCP:** report flags (idle, new device, Athena/Lightstep mismatch, error endreason) are a list of rule functions, so a new flag adds a function rather than another `elif`.
- **SRP and shared-vs-specific:** mechanism (call Athena or Lightstep, render a table) reuses `src/lib` and existing helpers; business rules (which devices are tracked, what counts as idle) stay in
  this pipeline. One module per job: roster, athena source, lightstep source, merge, render.
- **Module-boundary exceptions:** each boundary raises its own small hierarchy (`UsageTrackingError` base) instead of leaking `botocore` or HTTP exceptions.
- **One config convention:** a frozen dataclass loaded by a single `load(path)` function.
- **Logging and FCID:** the CLI's first statement is `init_logging()`; it logs run start, external-call start (DEBUG) and success with duration (INFO), failure once at the catching layer, and run end;
  query parameters go through `redact_params()`.
- **Architecture diagram:** this is a new module, so there is no "before"; UT-1 authors the planned structure and UT-7 regenerates it from the tree, tests excluded (`architecture-diagrams.md`).

## Task overview

- **UT-1** — Prior-art audit and design review (docs only): resolve the two open decisions, module map, Protocols, planned diagram.
- **UT-2** — Roster file and loader: `config/tracked_households.yaml`, validation, `track` flag.
- **UT-3** — Athena source: queries plus a fetcher for sessions, all-devices-per-household and error detail.
- **UT-4** — Lightstep source: request counts and trace ids per device, from the local export (default) or live (`--live-lightstep`).
- **UT-5** — Merge and rules: per-person metrics, flags, 7-day trend.
- **UT-6** — Markdown report renderer to the agreed format.
- **UT-7** — CLI entry point, failure handling, README with the cron line, `SCRIPTS.md`, `CONTEXT.md`, final diagram.

## Definition of done

`python -m src.pipelines.usage_tracking.scripts.run_daily_usage_report --date <D>` writes `output/reports/usage/<D>.md` for every `track: true` household, flags unknown devices and the other
anomalies, and exits non-zero with a "report not generated" note when auth or a query fails. The roster is the only input a user edits. Tests are green with no network, the design rules above hold,
the README documents the cron line, and `SCRIPTS.md` and `CONTEXT.md` are updated.

## Perspectives not covered

- Other event types (navigation, DRM) and non-sm-vod playback paths.
- Alerting or delivery: a missing or alarming report is only visible by reading the file or the cron log.
- Historical backfill: the job reports one date per run; the 7-day trend is read from Athena, not from stored reports.
- Device identity changes: a person who gets a new device shows up as a new-device flag plus an idle old device until the roster is edited by hand.
- Athena SSO lapse over a long absence: the job fails loudly but cannot log in interactively.
