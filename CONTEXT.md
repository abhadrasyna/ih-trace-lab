# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `investigations/incident-summaries/` holds one Markdown summary per incident (from Teams Copilot), named `YYYY-MM-DD_<ticket>_<slug>.md`; its `README.md` has the Copilot prompt and an index,
  `_TEMPLATE.md` the headings. First entry: INC0256822.

- `investigations/mtn-monthly-error-code-analysis/` is a recurring Athena-only monthly error-code campaign across all MTN OpCos (scripts so far: `profile_error_code.py` and
  `summarize_error_devices.py`, counts-only evidence for the MEC-27 business/technical question, helpers in `scripts/mec_lib/`): local `data/athena/` (gitignored) and `output/`, `RETENTION.md`, and
  `docs/{README,usage}.md` where `usage.md` documents every script as it is added. `docs/conviva-metrics-reference.md` lists the Conviva QoE metric definitions (2026-10-11) and which are computable
  from `unified_sessions`; `docs/monthly-error-code-pipeline/` holds the MEC tasks and stories.
- `investigations/ctap-smvod/` is multi-tenant (story `docs/archive/ctap-smvod-multitenant/`, MT-1..MT-10 done; pilot Zambia, results in `docs/2026-10-08-zambia-pilot-results.md`): `run_pipeline.py`
  runs every tenant with Lightstep input for the date by default, `--tenant` restricts to one; Step 0 (`check_lightstep_inputs.py` + `scripts/lib/lightstep_inputs.py`, bypass `--skip-input-check`)
  validates the manual Lightstep CSVs first (presence, part numbering, schema, tenant, `smvod-ts` UTC-day coverage); inputs/outputs live under `<TENANT>/` folders (ZA history `git mv`'d); the merge's
  `busUnitId` guard protects the shared Zambia/Ghana Lightstep project; the 1xxx/6xxx error report (CSV + xlsx) has an `is_wv` column via `scripts/lib/webview.py`. `analyze_error_report_breakdown.py
  --all-codes` reads `setupsession_with_outcome.csv` directly (includes 3016/E31012); `run_athena_error_eventdata.py` (catalog `ctap-smvod-error-eventdata`) exports raw `PLAYER_ERROR` eventdata and
  `flatten_error_eventdata.py` (+ `--split-by-errorcode`) flattens it into columns, both run as `run_pipeline.py` Steps 6f/6g (`--skip-error-eventdata`) and `summarize_error_eventdata.py` crosstabs
  them. `extract_household_error_eventdata.py --report-csv <error-report csv> --tenant ZA` pulls the local `*_error_eventdata.csv` rows for a report's sessions (matched on the eventdata `sessionid`,
  householdId/deviceId joined back). `run_athena_household_debug_events.py --report-csv <csv> --tenant ZA --from/--to YYYY-MM-DD` live-queries EVERY debug event for the report's `clientid`
  (`deviceId:householdId`) pairs (catalog slug `ctap-smvod-household-debug-events`). `run_athena_session_bandwidth.py` + `analyze_bandwidth_vs_failure.py` + `chart_bandwidth_vs_failure.py` (usage §7f,
  findings in `docs/2026-10-29_ZA_bandwidth-vs-playback-failure.md` for 24 Oct, and `docs/2026-10-30_ZA_bandwidth-vs-playback-failure_data-{28,29}Oct.md`) test bandwidth vs failure per sessionid.
  `extract_error_report_1xxx.py` (`--date` or `--from/--to`, `--tenants`, default ZA,GH,ZM) exports the 1xxx-only error sessions (not limited to position_not_moved) for several tenants at once, one
  CSV/XLSX per tenant in `output/<TENANT>/`. `rank_households_by_error.py --xlsx` ranks households by distinct error sessions in such an xlsx. `combine_error_code_by_opco.py` (optional `--from/--to`,
  `--codes`) merges the per-code flat files from all opcos into one XLSX per error code (sheet per opco, `date` column) in `output/error_code/<code>/`. `summarize_tenant_status.py --date DDMMYYYY`
  (run by hand after the pipeline) writes the ZA/GH/ZM cross-tenant daily status table to `docs/YYYY-MM-DD-tenant-status-summary.md` (UTC day; first one `docs/2026-10-08-tenant-status-summary.md`).
  `docs/usage.md` documents the layout, per-tenant export rule and how to add a tenant. `docs/2026-10-08-zm-6007-test-device-not-allowed.md` summarises a ZM Shaka 6007 case (MDRM 6211 "Test device not
  allowed"). `count_error_arrival_rate.py` (`--codes 6007,1003|6xxx|all|families` default 1xxx/3xxx/6xxx, `--from/--to`, `--tenants`, `--detail`, `--chart` day-wise line chart to
  `output/error_code/charts/`, top-N codes + "other" via `--chart-top`) sums sessions and unique households impacted per day per code across tenants from
  `output/<T>/daily/*_shaka-error-{session,hhid}.csv` (read-only; mean excludes first/last partial day; writes `output/error_code/arrival_rate_<from>_<to>.csv`). `count_error_by_content.py`
  (`--from/--to`, `--tenants`, default ZA) counts 6xxx sessions and unique households per content (per code + `_rollup`); `find_codec_support_content.py` (`--codec ec-3`) lists the content of error
  sessions whose device reports a codec probe as supported in the flattened eventdata (a device capability, not the content's codec). `compute_concurrent_playback.py` (`--date`, `--tenants`) writes
  per-minute concurrent sessions per UTC day from the CSV and Athena exports (three views, last debug event as an estimated end) and `chart_concurrent_playback.py` plots it via `src/lib/charts` (CH-6
  pilot). `run_athena_session_ingest.py` (catalog `ctap-smvod-session-ingest`) exports per-session `ingest_timestamp` from `unified_sessions` and `chart_playback_attempts.py --time-field ingest`
  charts attempts by when rows landed in Athena; `run_athena_debug_sessions.py` (catalog `ctap-smvod-debug-sessions`) exports the distinct debug-events sessions for a day, and
  `compare_lightstep_athena_sessions.py` (`--debug` for the 3-way) diffs Lightstep vs `unified_sessions` (vs debug) session sets, writing `output/<T>/<date>_lightstep_vs_athena_sessions.csv`;
  `build_session_comparison_daily.py` (`--from/--to`, `--tenants`, default all tenants) appends those counts, like the adoption reports, into `output/<OPCO>/daily/<YYYY-MM>_session-comparison.csv`
  (one row per `session_date`). `analyze_ebvs_release_coverage.py` (`--date`, `--tenant`) joins the Athena `playback_outcome` per session with the Lightstep SetupSession (`smvod`) and Release
  (`smvod-release`, the ninth export kind) session sets and reports per outcome how many lack a Release (ZA 2026-10-30: EBVS 91% vs DESTROY 26%). `run_3016_subcategory_report.py` (`--opco`, `--date`
  or `--from/--to`) reads the local flat error eventdata and writes `output/<OPCO>/subcategory_3016/<date>_subcategory_{summary,events}.csv`, splitting 3014/3015/3016 into the 5 triage sub-categories
  (rules in `classify_3016_subcategory.py`; documented in `docs/usage.md` §7d; `--drm` adds mDRM device columns via `build_3016_drm_link.py` and writes `<date>_subcategory_device_summary.csv` via
  `build_3016_drm_device_summary.py`). `analyze_drm_funnel.py` (`--opco`, `--date`; `--drm-dir`) writes the daily session → DRM license → error funnel from the saved mDRM Lightstep exports,
  `analyze_mdrm_quality.py` the license-chain quality report and `analyze_mdrm_devices.py` the device/`brRef` policy report (all in `docs/usage.md` §7e; outputs go to `output/<OPCO>/drm-analysis/`
  with `csv/` and `charts/` subfolders via `scripts/lib/drm_output.py`; the `stages` chart is `scripts/lib/funnel_stages_chart.py`; `run_pipeline.py` runs the three as Steps 6i-6k under one
  `--skip-drm-reports`; shared readers `scripts/lib/drm_*.py`). Constrained by `docs/refactor/`.
- `investigations/shaka-6001/` (2026-11-06) — Shaka 6001 across ZA/GH/ZM: which device models are impacted and how many have `drmenabled` in the debug table; reuses local `ctap-smvod` data,
  `README.md` lists sources; gitignored `data/athena/` and `data/lightstep/` hold fetched inputs. Story `docs/plan/shaka-6001-za-upgrade-analysis/` (ZA before/after the 2026-11-04 upgrade): SU-1..SU-4
  done — `scripts/lib/{analysis_config,period,local_data,athena_fetch}.py` (config in `config/analysis.yaml`, version-first before/after classifier, local loader with gap report, injected-client fetch
  of missing dates), `scripts/build_enriched_events.py` (deduped per-event table with UA fields and period, to `output/ZA/`); promoted shared libs `src/lib/{user_agent,playback,ranking,debug_events}/`
  (`ctap-smvod` re-exports them); SU-5/6/8/10 code done (`analyze_before_after.py`, `analyze_versions_devices.py`, `fetch_guest_login_redirects.py` with two registered queries, `build_6001_cohort.py`;
  real Athena fetches for SU-8/SU-10 not yet run); SU-7, SU-9, SU-11..SU-15 open.
- `investigations/inc-latency-shaka-1xxx/` (INC0256345 & INC0256143, latency + Shaka 1xxx errors) — HAR in gitignored `data/har/`; `scripts/analyze_har_latency.py --har --out` summarises MPD and
  audio/video/init segment timing phases (p50/p90/p95/max, slowest requests, throughput, repeated requests) into `output/har-latency-mpd-segments.md`; tests in `tests/`; findings in
  `docs/inc-latency-shaka-1xxx-notes.md`; shareable summary in `docs/har-latency-summary.md`.
- `investigations/mtn-sa-span-attribute-audit/` — ad hoc audit of MTN ZA Lightstep span attributes, driven live via the Lightstep MCP tools (tenant resolved through
  `scripts/resolve_tenant.py`/`config/tenants.yaml` to Lightstep project `mcs-go-prod-iye9omdf-eu`, EU region). `docs/sample-span-ctap-server.md` and `docs/sample-span-households-core-server.md` each
  capture one full span's attributes (identity, timing, tags, reporter/process info) pulled via `get_stored_trace`/`query_spans`; the second file also tallies a key-by-key diff against the first (48
  common keys, 37 differing properties total). `docs/household-device-field-naming-finding.md` resolves one of those diffed fields: within `ctap`, exactly 3 "shared"-catalogue APIs
  (`shared_content`/`categorySpecific`/`sharedAsset`) emit `sessionInfo.logHouseholdId`/`sessionInfo.logDeviceId` with zero overlap against the 31 other APIs' `sessionInfo.householdId`/`deviceId` —
  determined by `request.api`, not by service or `sessionInfo.guestMode` (which only correlates, 89%/67% split, not a clean predictor); backing `query_timeseries` queries + per-API/per-guestMode
  counts live in `data/lightstep/ctap-household-device-field-naming-by-api.csv` and `data/lightstep/ctap-household-field-naming-by-guestmode.csv`. `docs/mtn-sa-span-attribute-audit-notes.md` is the
  investigation's still-TBD running-notes file.
- `src/lib/token_gen/` (Tool, README inside; tests in `tests/lib/token_gen/`) — `python -m src.lib.token_gen.cli <householdID> [--expires-in 3600]` runs the two-step Synamedia flow (client-credentials
  token at `auth.synamedia.com`, then `silent-login/create-token`) with stdlib `urllib`; `SYNAMEDIA_CLIENT_ID`/`SYNAMEDIA_CLIENT_SECRET` come from the environment or the gitignored root `.env`.
- `docs/refactor/` — a generic (Python-scoped) refactor playbook (`README.md` index + `design-principles.md`, `code-deduplication-and-taxonomy.md`, `planning-protocol.md`,
  `logging-and-correlation-id.md`, `process-discipline.md`, `python-hygiene-and-automation.md`, `architecture-diagrams.md`, `code-review-checklist.md`) distilling this repo's own `docs/archive/`,
  `docs/plan/`, and `PYTHON_DESIGN.md` history into a reusable method for refactoring a different ad hoc Python legacy tree later. No project-specific names (entities, tenants, repos) appear in it by
  design — it is meant to be read by a future, unrelated Python project.
- `docs/guides/lightstep-querying.md` — read-first checklist for any Lightstep MCP query: resolve tenant, read `knowledge/mtn-sa-lightstep-{span-attributes-by-service,query-templates}.md` and
  `queries/lightstep/index.md`, topic-doc table, recurring pitfalls. Pointed to from `AGENTS.md` Domain conventions and audited by `session-close` row 6.
- `docs/guides/chart-guidelines.md` — matplotlib chart standard (dark theme, palette, font fallback, headless figure recipe) matching the shared `src/lib/charts/` package (`theme`, `fig`, `axes`,
  `title`, `header`, `signed_line`, `bar`, `stacked_bar`, `pie`, `errors`, `output`). `ChartTheme.series` is an ordered 5-colour palette (status colours `green`/`red`/`amber` stay out of it) for
  multi-series charts; `render_stacked_bar` (MDRM-2a) draws stacked bars with `green`/`red` reserved for success/failure. `output.write_chart_png` saves PNGs to
  `<investigation>/output/<TENANT>/charts/`, apart from the CSV/XLSX reports. Pilot: ctap-smvod `chart_concurrent_playback.py`/`chart_playback_attempts.py`; other investigations adopt the layer in
  their own stories (story `docs/archive/shared-chart-infra/`).
- `docs/archive/chart-guide-code-alignment/` (done, archived 2026-10-25) and `docs/archive/chart-funnel-visual-consistency/` (open) — chart-improvement stories: the first aligned shared title/axis
  code and the guide (CA-1 `title.draw_title` at 16/10 pt, CA-2 `axes.format_value_axis`, CA-3 guide/CONTEXT alignment, CA-4 `amber` status colour and 5-colour palette); the second brings the
  ctap-smvod DRM funnel charts to the look of the (AI-generated, uncommitted) mockups in `investigations/ctap-smvod/output/ZA/charts/modified/`.
- `docs/usage.md` — command reference for every `src/pipelines/aws_access_cli/scripts/` variant (daily/weekly/monthly orchestrators, historical backfills, single reports, catalog query, header
  seeding). The daily/weekly/monthly orchestrators catch up missed periods by default (lookback 7 days / 4 weeks / 3 months; `--no-catch-up` and `--force` documented there); existing outputs are
  skipped before Athena runs.
- `.github/hooks/session-context.json` — a native Copilot CLI `sessionStart` hook (not a git hook) that auto-injects a short reminder into every new/resumed session: read `CONTEXT.md`, state
  `CONTEXT.md ✓`, confirm scope when files aren't named, and state a plan + wait for go-ahead before non-trivial changes. Added to cut the highest-recurrence rows in `suggestions.md`
  (`wait-for-explicit-go-ahead-before-editing`, `state-context-md-checkmark-explicitly`, etc.) at the source instead of only catching them after the fact in `session-close`. Injects a short pointer,
  not the full `AGENTS.md`/`CONTEXT.md` text, to avoid adding token cost every session.
- `AUTOMATION.md` (root) + `.github/hooks/autopilot-checkpoint.json` / `scripts/dev/hooks/autopilot_checkpoint.py` — diagnosed from the `src-lib-migration` epic's 2026-10-02 run, which executed all 24
  task segments inside one single-agent session with no re-check between segments (the direct cause of `suggestions.md`'s `re-read-context-on-resumed-task-segments` and repeated
  `state-plan-before-editing`/`wait-for-explicit-go-ahead-before-editing` rows). `AUTOMATION.md` is the how-to for running a multi-story epic via one sub-agent per story instead (token cost scales
  with story count, not story count squared, and each sub-agent's own first turn satisfies Steps 1-3 fresh). `autopilot_checkpoint.py` is the fallback for when sub-agent delegation genuinely isn't
  available: an `agentStop` hook that forces a plan/go-ahead checkpoint every 5 turns regardless of commits, complementing (not replacing) `session_close_on_commit.py` (commit-triggered) and
  `session-context.json` (`sessionStart`-triggered only).
- **Copilot Memory is enabled** (`/memory on`, confirmed 2026-10-01) — a per-user CLI account setting, not a repo file; there is nothing under this repo to look for. Intended to reduce the
  `avoid-broad-filesystem-finds`/`avoid-mid-session-rereads` rows in `suggestions.md` by letting the CLI recall repo-structure facts across sessions instead of re-discovering them each time.
- `docs/archive/tenant-registry/` — story complete: `config/tenants.yaml` is now the canonical MTN tenant-identifier config for all 4 confirmed opcos (Go ID, Matisse Project/Client Tenant ID, Athena
  Tenant ID, Lightstep project/region, shared-project disambiguation attribute); `src/tenant_registry/` loads it and resolves per-system query contexts (`TenantRegistry`/`QueryTarget`); this assistant
  must consult it (via `scripts/resolve_tenant.py` or the loader directly) before any Lightstep/Matisse/Athena MCP call, per `docs/guides/tenant-resolution.md`'s CLI-first protocol. TR-1's scratch
  probe was confirmed against real, human-reviewed Lightstep MCP data (dedicated ZA project + shared Ghana project disambiguated by `busUnitId`) before any production code was written. Later addition:
  `--system lightstep_mdrm` (`LightstepMdrmQueryTarget`) resolves the US project `mcs-mdrm-production` with the mDRM-internal `tenantId` filter (ZA = `qfrtzlcj`, not the GO id); ZA, GH (`bb245tf0`)
  and ZM (`lcci3mag`) are registered.
- `docs/archive/query-catalog/` — story complete: `queries/athena/` + `queries/lightstep/` now provide a deduplicated, parameterized-template query catalog harvested from `github_copilot`'s 3
  `QUERY_CATALOG.md` files plus `lightstep-query-templates.md`; the Athena/Lightstep harvest scripts are in `scripts/dev/`, the query indexes/templates live under `queries/`, the query workflow guide
  lives at `docs/guides/query-catalog.md`, and the ported (not yet run) Athena DDL-cache tooling plus `knowledge/README.md` live under `knowledge/` / `scripts/athena/`.
- `docs/archive/project-taxonomy/` — story complete: `docs/guides/project-taxonomy.md` now defines the four categories, folder skeletons, prior-art checklist, pipeline cron-cutover procedure, and PT-7
  data/knowledge conventions; `config/data_paths.yaml` is the path-template source of truth; `scripts/dev/check_project_taxonomy.py` audits unclassified top-level dirs; and
  `.github/skills/investigation-doc-sync/SKILL.md` defines the deferred cross-session case-doc sync workflow. `structure.md` remains the canonical target-tree reference for this story and
  `functional-code-taxonomy`.
- `docs/archive/functional-code-taxonomy/` — story complete: `docs/guides/functional-code-taxonomy.md` now maps the six shared `src/lib/*` modules, states the shared-vs-specific test, records the
  `query-catalog` boundary, and documents the delegated cross-project duplicate-check. `src/lib/{athena,report_render,har}/protocols.py` and `src/lib/paths/{protocols.py,config.py}` now provide the
  shared Protocol/path-resolution seams, with tests; `scripts/dev/generate_code_registry.py` inventories reusable code outside `scratch/`. Sibling to `project-taxonomy` (categories vs. shared code)
  and `query-catalog` (SQL text vs. execution code).
- `docs/plan/lightstep-daily-export-automation/` — story in progress (LX-1 done, LX-2..LX-7 open): replace the hand-exported daily Lightstep CSVs with an API pull. LX-1 findings are in its
  `stories.md` (seven kinds reproduce via `query_timeseries`; `smvod-ts` derived approximately; ~7-day Lightstep retention). Probes: `scratch/2026-11-01_lightstep_export_api_feasibility_probe.py`
  (per-kind full-day key-set diff against hand CSVs) and `scratch/2026-11-01_lightstep_smvod-ts_derive_probe.py` (derives `smvod-ts` from `smvod` points). LX-9a added `scripts/lib/lightstep_stitch.py`
  (pure merge of per-window series or CSV rows) and `read_rows` in `scripts/lib/lightstep_csv.py`; LX-9b added `scripts/lib/lightstep_parts.py` (JSON part store with manifest, verified resume) and the
  `--part-hours`/`--fresh` flags; LX-9c added `scripts/lib/lightstep_export_checks.py` (sanity checks (a)-(c) per kind; a broken output fails the kind, a missing part is only logged) and the runner's
  `cleanup_parts`, which deletes `tmp/lightstep-export/<TENANT>_<date>/` only when every kind is ok, no foreign-kind parts remain and the input check passed; LX-9d is open.
- `docs/archive/scratch-script-registry/` — story complete: root `SCRIPTS.md` is now generated from the live `scripts/` + `scratch/` tree via `scripts/dev/generate_scripts_registry.py`;
  `scripts/dev/promote_scratch_scripts.py` provides manual promotion with registry refresh; `scratch/SCRATCH.md`, `AGENTS.md`, and the repo-local `.github/skills/session-close/SKILL.md` enforce the
  delegated duplicate-check and close-out regeneration workflow; `tests/dev/` covers both CLIs.
- `docs/archive/reference-knowledge-harvest/` — story complete through RKH-17: `knowledge/` now contains the harvested VOD asset mapping/pipeline references, MTN ZA Lightstep tag/query references,
  Applause Athena/CSV gotchas, adoption playback-outcome gap notes, CTAP-SM-VOD playback/CDN methodology docs, MTN/TIM Play tenant+DRM references, the 3 root knowledge ports, and the SRE Jira project
  reference. The story remains extensible — future `github_copilot/*` folders would reopen it by appending new `RKH-N` tasks rather than creating a new story.
- Story-archiving is now scripted and self-triggering: `scripts/dev/archive_completed_story.py <slug>` (epic-aware; refuses incomplete slugs) does the `git mv` + cross-reference rewrite + 200-char
  reflow described in `docs/plan/README.md`'s "Archiving a completed story" section and stages the result for review/commit; the non-blocking `story-archive-check` pre-commit hook
  (`scripts/dev/hooks/check_unarchived_stories.py`) warns when a story looks complete but hasn't been archived yet. Separately, `.github/hooks/session-close-trigger.json` (native Copilot CLI
  `sessionStart`/`agentStop` hooks, backed by `scripts/dev/hooks/session_close_on_commit.py`) detects when `HEAD` moved during a turn (i.e. a commit just landed) and forces one more turn whose prompt
  asks the agent to invoke the `session-close` skill immediately, instead of relying on the end of the whole session to remember to do it.
- `docs/archive/src-lib-migration/` — epic: real, tested implementations of `functional-code-taxonomy`'s six `src/lib/*` modules (`auth`, `athena`, `csv_io`, `report_render`, `har`, `curl_to_python`),
  ported/refactored from `github_copilot` (read-only reference), one story per module. `athena-lib-integration` is the exception — it wires in `/Users/abhadra/myWork/myOffice/athena-mcp-server` (an
  already-independent, tested repo with the shared `athena_runner` execution stack) as a git submodule and adapts to it, rather than re-porting a fifth copy of that logic.
  `auth`/`csv_io`/`curl_to_python` additionally define their own `Protocol`s here, deferred by `functional-code-taxonomy` FCT-2. `athena-lib-integration` is complete through ALI-6 (ALI-7 is
  docs-only); see `docs/archive/src-lib-migration/README.md`'s Stories table for the other five stories' status and first unchecked task.
- `vendor/athena-mcp-server` — pinned git submodule (see `docs/guides/submodules.md` for init/update steps; `git submodule update --init` after cloning, plus `pip install -e vendor/athena-mcp-server`
  since the submodule's `athena_runner` package isn't on PyPI). `src/lib/athena/adapter.py` is a thin DIP adapter delegating to it — no `query_executor`/`aws_clients` execution logic is duplicated in
  `ih-trace-lab` itself; `src/lib/athena/exceptions.py` defines this module's own exception hierarchy so callers never need to catch `athena_runner.exceptions.*` or raw
  `botocore.exceptions.ClientError` directly.
- `src/lib/athena/batch.py` + `cache.py` — bounded-concurrency batch submission (`BatchQueryRunner`, pool size from `athena_runner.config.RunConfig.max_concurrency`) with a fingerprint-keyed TTL
  result cache (`InMemoryTtlCache`), for consumers submitting multiple independent queries at once (e.g. per-tenant/per-day fan-out). One query's failure never blanks out the batch's other results
  (`AthenaBatchExecutionError` carries both partial results and failures).
- `src/lib/athena/progressive.py` — progressive scope-widening query runner (`ProgressiveQueryRunner`): runs a narrow scope first, widens only if a consumer-supplied `SufficiencyCheck` says the result
  isn't enough, stops when the consumer's `ScopeSequence` is exhausted (or a `max_rounds` backstop is hit, guarding against a misbehaving collaborator pair), and combines rows across every scope
  actually run.
- `src/lib/report_render/writers.py` + `factory.py` — Strategy-based report writers (`MarkdownTableWriter`, `CategoryBreakdownWriter`, `StatisticalWriteupWriter`), selected via a Factory Method
  (`make_report_writer(shape)`) keyed by shape (`"markdown_table"`/`"category_breakdown"`/`"statistical_writeup"`), replacing the 8+ duplicated `github_copilot` originals cited in
  `report-render-lib-migration/stories.md`'s RRM-1 audit. Future consumers call `make_report_writer(shape)`; none import a concrete writer class directly.
- `src/lib/har/loader.py` — `JsonHarEntryLoader` implements `HarEntryLoader` (`functional-code-taxonomy` FCT-2's `Protocol`), replacing the 4 duplicated `github_copilot` HAR `log.entries` loaders
  cited in `har-lib-migration/stories.md`'s HLM-1 audit (`applauseInvestigation/scripts/analyze_har.py::iter_entries()`,
  `vod-playback-timing-probe/scripts/{extract_content_ids_from_har.py,summarize_har_playbacks.py}::_load_entries()`, `vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()`).
  Accepts `str | Path | an open file handle`; `load_json_entries()`'s JSON-filter/response-parse step stays out of scope as project-specific logic for a future consumer.
- `src/lib/auth/protocols.py` + `sso.py` — `AuthProtocol` (`ensure_session`/`refresh_if_expired`), generalized from `athena_runner.sso_auth.SsoCredentialRefresher`'s proven shape, and its concrete
  `SsoAuth` implementer. `SsoAuth` is constructor-injected with `refresher_factory`/`session_factory` collaborator callables (rather than one bound collaborator) because the real
  `SsoCredentialRefresher` binds a single profile per instance while `AuthProtocol`'s methods take `profile_name` per call; it never builds its own `boto3` object or reimplements the SSO refresh
  polling loop.
- `src/lib/csv_io/protocols.py` + `csv_file.py` — split `CsvReaderProtocol`/`CsvWriterProtocol` (ISP) plus stdlib-backed `CsvFileReader`/`CsvFileWriter` for raw CSV I/O, distinct from
  `report_render`'s formatted-output Strategy (`csv_io` owns getting rows in/out of files; `report_render` renders already-read/normalized rows). Matches `csv.DictReader`/`csv.DictWriter` defaults
  exactly, per `csv-io-lib-migration/stories.md` CIM-1's requester-approved file-boundary audit.
- `src/lib/curl_to_python/protocols.py` + `converter.py` — `CurlConverterProtocol` (`convert(curl_command) -> str`) and its concrete `CurlToRequestsConverter`, built ahead of a proven-duplication
  trigger per this epic's explicit authorization (no existing `github_copilot` file was found to replace — see `curl-to-python-lib-migration/stories.md`'s CPM-1 finding). Parses curl's
  method/URL/headers/data grammar only (any other flag/quoting form raises `UnsupportedCurlFlagError` by name rather than producing silently-wrong output) and renders Python `requests.request(...)`
  source text; never executes the converted request.
- `src/lib/logging/context.py` — minimal FCID (flow-correlation-id) `contextvars` propagation slice (`bind_fcid`/`current_fcid`/`FcidLogFilter`), built as an `athena-lib-integration` ALI-5
  prerequisite so FCID survives a `ThreadPoolExecutor` boundary. `docs/archive/logging-framework/` has now started implementing the rest of FCID-1's deferred runtime wiring around it:
  `src/lib/logging/bootstrap.py` mints/binds one FCID per entry point, `src/lib/logging/setup.py` injects `%(fcid)s` on every handler, and `src/lib/logging/redact.py` provides allow-list-based
  parameter masking.
- `docs/archive/logging-framework/` — story complete (LFR-1..8): closes the deferred FCID/runtime gap flagged by both `src/lib/logging/context.py` and `pipeline-migration`'s README. It added
  `src/lib/logging/bootstrap.py`'s `init_logging()`, handler-level FCID injection, and allow-list parameter masking; defined the minimum logging contract in
  `docs/refactor/logging-and-correlation-id.md`; applied that contract to `src/lib/athena/adapter.py` plus the `aws_access_cli` adoption/Shaka/position business-logic modules; wired `init_logging()`
  into every `src/pipelines/aws_access_cli/scripts/run_*.py` entry point before argument parsing; made report-preview table output opt-in via `--preview`; made the contract binding in
  `docs/refactor/code-review-checklist.md`; retrofitted every `investigations/ctap-smvod/scripts/*.py` entry point with `init_logging()` plus start/end run logs; retrofitted every root
  `scripts/dev/*.py` and `scripts/athena/*.py` entry point (plus `scripts/reference_diagram/main.py` and `scripts/resolve_tenant.py`); routed `setup_logging()`'s stream handler to stderr so
  retrofitted CLIs whose stdout is their actual product output aren't polluted by log lines; and added a non-blocking `logging-contract-check` pre-commit hook that flags any new entry point skipping
  `init_logging()`, so this class of gap gets caught automatically going forward.
- `src/lib/logging/setup.py` — the canonical `setup_logging()` entrypoint (moved here from `logs/setup_logging.py` so code and its own generated runtime artifact, `logs/app.log`, aren't colocated in
  one directory). Resolves its log directory from a new `logs_root` key in `config/data_paths.yaml` (default `logs`) instead of a hardcoded path relative to the module file, consistent with the
  project's single-config-loading-convention guidance; `logs/` itself still holds the generated `app.log` and its `.gitignore`. All 4 prior `logs.setup_logging` import sites were updated to
  `src.lib.logging.setup`.
- `docs/plan/pipeline-migration/` — epic: ports `aws-access-cli` (→ `src/pipelines/aws_access_cli/`, importable package name, external slug stays `aws-access-cli`; pipeline category) and
  `ctap-smvod-session-report` (→ `investigations/ctap-smvod/`, recurring-campaign category, incl. manual-Lightstep-step relocation) from `github_copilot` (read-only reference), replacing their
  duplicated executor/auth/SQL/output logic with `src/lib/*`, `query-catalog`, and `project-taxonomy` PT-7's ISO-prefix path convention respectively. Both stories ran in parallel in isolated git
  worktrees (2026-10-03). `ctap-smvod-investigation-migration` is **done** (CSM-1..7, 57 tests passing); `aws-access-cli-pipeline-migration` is implemented through AAM-4 and AAM-6 (25 tests passing),
  with AAM-5 (PT-6 cron-cutover for the 3 live crontab entries) left open — `Owner: human (crontab access required)`, operator runbook in that story's own `session-log.md`.
- `src/lib/csv_io/existing_output.py` (`csv_has_data`) — pre-flight "does this CSV already hold the data?" check (file exists with a data row, optionally for a given `session_date`). Every
  `aws_access_cli` runner in `scripts/common.py` and the `scripts/athena/*` exporters call it before firing Athena and skip unless `--force` is passed (also forwarded by the
  daily/weekly/monthly/backfill wrappers). `investigations/ctap-smvod/scripts/run_athena_playback_outcome.py`/`run_athena_debug_events.py` do the same via `lib.runtime.should_skip_athena`, and
  `run_pipeline.py --force` forwards the override.
- `src/lib/csv_io/monthly_store.py` (`MonthlyCsvStore`) — restores the pre-migration `AdoptionReportStore`'s "append one day's row(s) into a running month file" behavior that
  `aws-access-cli-pipeline-migration` had dropped in favor of a brand-new per-day snapshot CSV for every artifact. `replace_date(path, date, rows)` drops any existing rows for that date before
  appending the new ones (so reruns never duplicate), and works for both the wide one-row-per-date shape (adoption reports) and the long multi-row-per-date shape (Shaka error reports) since it just
  unions fieldnames rather than assuming a schema. `PathResolver.format_month_filename` names these `<yyyy-mm>_<artifact>.csv` for `--period day` runs; `PathResolver.format_perpetual_filename` (new)
  names an undated `<artifact>.csv` for `--period week`/`month` runs -- one file per tenant/cadence that accrues one row per run forever, matching the pre-migration repo's weekly/monthly accumulation
  convention, again keeping the new kebab-case artifact-naming convention rather than the old underscored style. `scripts/common.py`'s `_uses_append_store` (renamed from `_is_monthly_append`,
  broadened from day-only) now routes all three periods for the same 5 artifacts (`adoption-report`, `adoption-session-report`, `guest-session-report`, `shaka-error-hhid`, `shaka-error-session`)
  through `MonthlyCsvStore`, pointed at the month-file (day) or perpetual-file (week/month); gap-analysis artifacts and the position report are unaffected and keep one file per run.
- `src/pipelines/aws_access_cli/shaka_errors.py` (`KNOWN_ERROR_CODES`, `pivot_error_counts`) — ports the pre-migration `shaka_errors/column_merge.py`'s pivot: Shaka error reports are produced
  long-format (one row per errorcode) by `build_shaka_error_report`, but the on-disk file must be wide (one row per date, one column per errorcode), matching old `aws-access-cli` output exactly.
  `pivot_error_counts` orders columns as the 14 fixed `KNOWN_ERROR_CODES` first, then any column the target file has already discovered (read from its current header via
  `scripts/common.py::_existing_header_columns` before pivoting, so a previously-added code keeps its position), then brand-new codes this run (sorted) appended last; every column gets an explicit
  value for the date being written ("0" if that code didn't occur), while older rows missing a newly-discovered column stay blank via `MonthlyCsvStore`'s own union/`DictWriter` defaults -- reproducing
  the old repo's column_merge output byte-for-byte. Wired into `run_shaka_cli` for all three periods. Because the legacy weekly/monthly Shaka files had already accumulated months of history before
  this migration, any code they discovered only once keeps whatever column position it was first assigned back then -- an order this repo's brand-new, empty perpetual files can't rederive by sorting
  alone (two codes "new" to *this* repo's file in the same run sort alphabetically, which only matches the legacy order by coincidence). `scripts/seed_shaka_perpetual_headers.py` is a one-time,
  idempotent migration script that copies just the legacy file's header (no data rows) into this repo's perpetual file the first time it's created, so `_existing_shaka_pivot_columns` picks up the
  legacy-established order from this repo's very first write; it never touches a perpetual file this repo has already started writing to. Already run once (2026-10-05) for all 4 tenants' weekly and
  monthly `shaka-error-hhid`/`shaka-error-session` files.
- `docs/plan/reference-code-gap-migration/` — **epic** (promoted from a single story by its own GAP-1 task, 2026-09-30): ports the 10 `github_copilot` projects (~166 Python files) that neither
  `pipeline-migration` nor `src-lib-migration` cover, into 10 sub-stories tiered by effort/blocking (`README.md`'s decision log) — Tier 1 cheap (`applause-investigation-migration`,
  `astro-events-household-investigation-migration`, `shaka-6001-sa-investigation-migration`, `root-scripts-tool-migration`), Tier 2 medium (`vod-asset-ingestion-investigation-migration`,
  `mtn-zm-device-investigation-migration`, `mtn-network-traffic-tool-migration`, `root-investigations-migration`), Tier 3 blocked on two newly-promoted `src/lib/*` modules
  (`vod-playback-timing-probe-tool-migration` needs `mpd`, `smarttv-mtntv-tool-migration` needs `crypto_signing` — both modules to be built by `src-lib-migration`, not this epic). GAP-1 also flagged a
  correction to `project-taxonomy/structure.md`/`stories.md`: `vod-asset-ingestion-mapping` recategorized from `experiments/` to `investigations/vod-asset-ingestion/` (recurring campaign, per its own
  README); a second, similar tension for `vod-playback-timing-probe` (audit suggests "tool", `structure.md` still examples it under `experiments/`) was flagged but deliberately left unresolved for a
  future `project-taxonomy` session. `oasis-athena-mcp` was checked and confirmed not a gap (superseded by the `athena-mcp-server` submodule). Root `prompt.md` is now a pure router (no session-start
  protocol of its own) — each of the 10 sub-stories has its own `prompt.md`/`tasks.md`/`stories.md` and first unchecked task (all currently their own `<PREFIX>-1` audit task). Not yet implemented
  beyond GAP-1 — see `README.md`'s Stories table for which sub-story to pick up next. **2026-10-01:** cross-cutting constraint added requiring any sub-story that ports a CSV/report-writing script to
  adopt `PathResolver`'s naming helpers (`format_snapshot_filename`/`format_range_filename`/`format_rollup_filename`), not just its directory resolver — confirmed by source read that
  `shaka-6001-sa-error-analysis`, `mtn-zm-session-device-investigation`, `astro-events-household-report`, and `vod-playback-timing-probe` each still hardcode their own ad hoc output-path logic today;
  mirrors `pipeline-migration` AAM-4's already-designed task shape.

- `docs/archive/reference-folder-diagrams/` — story complete: `scripts/reference_diagram/` now supports per-project internal-import flowcharts, and `docs/reference-diagrams/` now indexes 12
  folder-level Mermaid pages (generated flowcharts plus hand-authored convergence/orchestration/state diagrams) covering every in-scope `github_copilot` migration folder except deliberately-excluded
  `oasis-athena-mcp`; the set makes `reference-code-gap-migration`'s tiering and its `src/lib/mpd/` / `src/lib/crypto_signing/` promotion decisions visible, not just prose.
- `docs/archive/flow-correlation-id-logging/` — story complete (design-only): defines the project's FCID (flow-correlation-id) convention — one id per run, minted once at each consumer's entry point,
  propagated via a `contextvars.ContextVar` (no manual parameter-threading through `src/lib/*` adapter methods), auto-injected into every log line via a `logging.Filter`. `stories.md` carries a
  sequence diagram (one Athena query inside one pipeline run) and a component diagram (FCID flowing through `src/lib/*` into all three migration epics' consumers); no `src/lib/logging/` module or code
  exists yet — that is deferred to a follow-up story once a real consumer (first candidate: `athena-lib-integration` ALI-2) needs it. Coordination notes were added to `src-lib-migration`,
  `pipeline-migration`, and `reference-code-gap-migration`'s `README.md`s pointing here. Cross-process FCID propagation (subprocess/cron boundaries) is explicitly out of scope, left open for later.
- `docs/archive/pre-implementation-design-review/` — story complete: a SOLID/clean-code/extensibility design review of all 18 not-yet-started stories across `src-lib-migration`, `pipeline-migration`,
  and `reference-code-gap-migration`, run before any of them starts producing code. `spec.md` is the full findings table. One low-risk finding was fixed directly: a blocking method-name/signature
  mismatch between `src/lib/athena/protocols.py`'s `AthenaClient` and `athena-lib-integration/stories.md`'s own ALI-2 class diagram, which would have failed that story's own task gate. A second
  finding (a design-time-diagram-discipline parity constraint for `reference-code-gap-migration/README.md`) was applied, then reverted 2026-10-01 at the requester's instruction as a self-introduced
  extension outside their stated review criteria — `spec.md`'s finding #11 row records this. **2026-10-01 follow-up: all 6 originally-flagged judgment calls resolved** (`spec.md`'s "Flagged for human
  decision" section now records each resolution) — (a) `src-lib-migration/README.md` gained a standardized two-assertion DIP-enforcement test pattern, applied to `athena-lib-integration`'s ALI-3 and
  `auth-lib-migration`'s AUM-3; (b) `report-render-lib-migration` gained a new `RRM-3` Factory Method task (`src/lib/report_render/factory.py`) selecting a writer by shape key, renumbering the prior
  RRM-3/RRM-4 to RRM-4/RRM-5; (c) `curl-to-python-lib-migration`'s CPM-1 framing corrected to cite its real confirmed consumer (a HAR-driven manual timing/latency investigation workflow), replacing
  the prior "no-citation/speculative" framing; (d) the task-authoring SRP nit (finding #7) was left as-is, no split; (e) `ctap-smvod-investigation-migration`'s CSM-2 class diagram fixed to show
  `RunPipeline` delegating to explicit `MergeScript`/`AnalyzeScript` collaborators instead of modeling their logic as inline methods; (f) `athena-lib-integration` gained two new tasks, `ALI-4` (audit
  existing `athena_runner` batch/cache support) and `ALI-5` (`src/lib/athena/batch.py` + `cache.py` — bounded-concurrency `BatchQueryRunner` + `InMemoryTtlCache`, both DIP-compliant), with the prior
  ALI-4 (doc pointers) renumbered to `ALI-6`. **2026-10-01, same-day extended review pass (user-requested, 8 dimensions + progressive query scoping):** grounded in a direct read of the
  `athena-mcp-server` submodule's source (not speculation) — found and fixed a real defect: ALI-5's just-committed batch design did not satisfy `flow-correlation-id-logging`'s own stated
  `contextvars`/`ThreadPoolExecutor` caveat (FCID would have silently vanished inside worker threads); ALI-5 now captures `copy_context()` on the calling thread before submitting work. ALI-2 gained a
  mirrored `src/lib/athena/exceptions.py` hierarchy (never leaking `athena_runner.exceptions.*`) and throttling retry/backoff (confirmed missing upstream in `query_executor.py`); ALI-5 now reuses
  `athena_runner.config.RunConfig.max_concurrency` (confirmed reserved-but-unconsumed upstream) instead of a redundant new constructor arg, and pre-builds all `AthenaClient` instances sequentially
  before starting its thread pool (`AwsClientFactory`'s shared-`boto3.Session` construction is not documented safe for concurrent calls). A new `ALI-6` task (`src/lib/athena/progressive.py`) adds a
  progressive scope-widening query runner — narrow scope first, widen only if insufficient, combine rows across every scope actually run — per the user's own 9th review requirement; the prior ALI-6
  (doc pointers) renumbered to `ALI-7`. `flow-correlation-id-logging/stories.md` gained a PII/secrets redaction rule (log `sql_fingerprint`, not raw SQL; allow-list param keys).
  `src-lib-migration/README.md`'s cross-cutting constraints gained 5 generalized rules beyond the `athena`-specific instances: exception-hierarchy-per-module, config-loading consistency (cite
  `src/lib/paths/config.py`'s `PathConfig`), import-cycle/dependency-direction (one-directional `src/lib/*` graph, future `test_no_import_cycles.py`), shared test-fixture dedup (future
  `tests/lib/conftest.py`), and the packaging/import-path gap (no root `pyproject.toml`/`conftest.py` yet — `python -m pytest`-from-repo-root is the only reason `from src.lib...` imports currently
  work; flagged as an open item for `pipeline-migration`'s first integration task).
- `ruff.toml` (root) — added 2026-10-03 after `make lint` surfaced 72 errors across 7 unrelated rule families (`DTZ007`, `EXE001`, `PLW1510`, `PIE810`, `G201`, `PYI018`, `TRY401`); root had no ruff
  config at all, so `ruff check` was silently defaulting to its full broad rule set rather than an intentional selection. Curated `select` to `E4`/`E7`/`E9` (core pycodestyle errors), `F` (pyflakes),
  `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM` (flake8-simplify), `C4` (comprehensions) — this is a lint-rule-selection gap only, separate from the still-open
  pytest-import-path/root-`pyproject.toml` gap noted above. An earlier `ruff check --fix` pass (run before this file existed) had also auto-unquoted `src/lib/auth/sso.py`'s `ensure_session(...) ->
  "boto3.Session"` annotation (UP037), which broke `test_ensure_session_does_not_construct_own_boto3_client` (an AST-based test enforcing SsoAuth never references `boto3` directly); re-quoted with `#
  noqa: UP037` and a pointer to the guarding test so future `--fix` runs don't regress it again.
- `docs/plan/session-trace-analysis/` — **epic** (2026-10-26): an analysis like `investigations/ctap-smvod/output/ZA/drm-analysis` that follows a `sessionId` from creation in `sm-vod` or `sm-linear`
  to where it fails. Its first story `linear-session-coverage/` (LC-1..LC-4, none started) fixes the defect that the ctap-smvod Lightstep export and merge were `sm-vod`-only, so linear sessions
  (confirmed in ZM and GH) showed up as `ctap_only` rows; it must stay tenant-agnostic (ids from `config/tenants.yaml`, session type from the `abr-vod-`/`abr-linear-` `sessionId` prefix) so ZA or any
  future tenant works with no code change. Second story `session-presence-funnel/` (PF-1..PF-5, none started): a daily report counting Lightstep sessions and tracing the same `sessionId`s into Athena
  `unified_sessions` and debug states, with ZA 2026-10-24 as the acceptance baseline (4,443 Lightstep sessions, 3,763 in `unified_sessions`, 3,901 in debug states, 542 in neither). Story order since
  2026-10-26: `session-error-model/` (EM-1..EM-5), `linear-session-coverage/` (blocks GH/ZM only; ZA has no linear), `session-presence-funnel/`, then `session-lifecycle-report/` (SL-1..SL-6, none
  started): a daily per-tenant summary of the furthest hop, paths, hop timing, cohorts and export completeness, built on EM, PF-4 and PF-8, for ZA, GH and ZM now and NG once exported.
- `config/tracked_households.yaml` and `src/pipelines/usage_tracking/` (`roster.py`, `errors.py`, `tests/`) — UT-2 of `docs/archive/household-usage-tracking/`: the roster of tracked households (full
  `hhid`, members with `device_id`, `track` flag); `roster.load(path)` validates it (duplicate `(tenant, hhid)` or `(tenant, device_id)`, empty hhid, a household with a missing or unknown `tenant` via
  `TenantRegistry`, non-bool `track`) and raises `RosterError`, `tracked()` returns only `track: true` households, and `resolve_config_path` takes `--config`, then `TRACK_CONFIG`, then the default.
  `tracked()` and `by_tenant()` return only `track: true` households, the latter grouped per tenant. The second household is a `track: false` placeholder.
- `src/pipelines/usage_tracking/athena_source.py` and `queries/athena/usage-tracking-*.sql` — UT-3: `SessionSource` Protocol with `LocalExportSource` (default, filters the tenant-wide ZA CSVs by
  roster household and device; a missing file raises `AthenaSourceError`) and `LiveAthenaSource` (`--live-athena`, injected query runner, month-aware debug table via `debug_table_name`); errors are
  fetched only for sessions whose outcome is `PLAYER_ERROR`.
- `src/pipelines/usage_tracking/lightstep_source.py` and `queries/lightstep/usage-tracking-smvod-by-device.md` — UT-4: `RequestSource` Protocol with `LocalExportSource` (default, reads
  `data/lightstep/<TENANT>/<date>_smvod.csv`, keeps roster `(hhid, device_id)` pairs; a missing file raises `LightstepSourceError`) and `LiveLightstepSource` (`--live-lightstep`, injected UQL runner);
  `request_counts` returns 0 for a roster device with no rows. No 5xx column.
- `src/pipelines/usage_tracking/merge.py` and `rules.py` — UT-5: pure, no-I/O model. `build_household_day` turns one Athena window (trailing 7 days), devices seen, errors and Lightstep rows into
  `HouseholdDay`/`PersonDay` (sessions, watch minutes from `event_end − event_start`, errors, top content, Lightstep requests, 7-day trend with zeros; a person with no data is idle, not missing).
  `rules.RULES` lists one function per flag (idle after `IDLE_DAYS`=3, error endreason, Athena-vs-Lightstep session-id mismatch, new device on `track: true` households only); `apply_rules` fills
  flags. `HouseholdDay.lightstep_traces` maps session id to its Lightstep trace ids (added in UT-6).
- `src/pipelines/usage_tracking/scripts/run_daily_usage_report.py`, `live_clients.py` and `README.md` — UT-7: `python -m src.pipelines.usage_tracking.scripts.run_daily_usage_report [--date] [--config]
  [--out-dir] [--live-athena] [--live-lightstep]` writes `output/reports/usage/<TENANT>/<date>.md` per tenant from the local ctap-smvod exports (default date: two days ago); a failure writes
  `<date>.FAILED.txt` ("report not generated") and exits 1. `live_clients` builds the live sources only on a `--live-*` flag. The README holds the cron line; after-diagram in
  `docs/archive/household-usage-tracking/architecture-after.md`.
- `src/pipelines/usage_tracking/render.py` — UT-6: `render_report(tenant, day, households) -> str` (pure; the CLI writes the file) renders title, summary, per-household table, per-person session
  detail (parent_session_id, endreason, error code/message for errored sessions, trace_id), Anomalies (full HHIDs) and the 7-day trend; `MarkdownTableRenderer` satisfies `ReportRenderer`; golden file
  in `tests/data/golden_report.md`.

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- `/Users/abhadra/github_copilot` is read-only reference (see `README.md`'s mission statement) — never create, edit, or delete anything there from this project; treat it as prior art to learn the
  "profile of work" from, not a shared codebase.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
