# Reference code gap migration — 2026-09-30 audit findings

> File-by-file plan input for GAP-1 (see `stories.md`). No task checkboxes here — this is evidence, not a working list. Produced by a background `explore` agent auditing all `.py` files (source
> + tests) under the 10 gap projects named in `prompt.md`, cross-checked against `src-lib-migration`'s 7 planned modules (`auth`, `athena`, `csv_io`, `report_render`, `har`, `curl_to_python`,
> `paths`) and their existing citation list.

# Audit scope and counting note

Audited the ten requested project trees under `/Users/abhadra/github_copilot/`. Counts below include source, package, and test `.py` files; virtual-environment files were excluded. Test files are
listed individually where present but classified as `script: test/support code`, because they do not represent migration implementation logic.

The reference tree contains approximately 166 relevant Python files. Existing planned modules are treated as already scoped: `auth`, `athena`, `csv_io`, `report_render`, `har`, `curl_to_python`, and
`paths`.

---

## 1. `vod-playback-timing-probe`

**Purpose:** Replays CTAP/VOD playback flows, extracts flow/auth information from HAR and cURL captures, and compares probe timing with captured playback behavior.

**Suggested category:** **tool** — reusable playback-probing utility with a substantial CLI/package surface, rather than a bounded case.

### Per-file audit

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/build_distributable.py` | 107 | Builds distributable probe bundle | script: business-logic | no duplication observed |
| `scripts/compare_har_vs_probe.py` | 121 | Compares HAR and probe timings | script: business-logic | no duplication observed |
| `scripts/discover_content_ids.py` | 220 | Discovers content IDs from playback data | script: business-logic | no duplication observed |
| `scripts/extract_content_ids_from_har.py` | 108 | Extracts content IDs from HAR | lib candidate: `har` | already cited: `extract_content_ids_from_har.py::_load_entries()` |
| `scripts/extract_flow_from_har.py` | 86 | Extracts reusable flow template from HAR | lib candidate: `har` | no duplication observed |
| `scripts/fill_license_step_from_har.py` | 211 | Fills flow license step using HAR | lib candidate: `har` | no duplication observed |
| `scripts/generate_timing_report.py` | 184 | Renders timing report | lib candidate: `report_render` | new duplication: `mtn-network-traffic/scripts/generate_timing_report.py` |
| `scripts/playback_probe/__init__.py` | 4 | Package marker | script: support code | no duplication observed |
| `scripts/playback_probe/auth.py` | 73 | Builds playback authentication data | lib candidate: `auth` | new duplication: `applauseInvestigation/analyze_athena_playback.py` auth handling |
| `scripts/playback_probe/ctap_client.py` | 188 | Calls CTAP playback APIs | script: business-logic | no duplication observed |
| `scripts/playback_probe/ctap_har_extractor.py` | 34 | Finds CTAP requests in HAR | lib candidate: `har` | new duplication: `scripts/playback_probe/curl_parser.py` HAR request extraction |
| `scripts/playback_probe/curl_parser.py` | 203 | Parses cURL commands and requests | lib candidate: `curl_to_python` | already cited: mtn-network-traffic converter |
| `scripts/playback_probe/distributable_manifest.py` | 75 | Creates distribution manifest | script: business-logic | no duplication observed |
| `scripts/playback_probe/fcid.py` | 22 | Handles FCID values | script: business-logic | no duplication observed |
| `scripts/playback_probe/flow/__init__.py` | 1 | Flow package marker | script: support code | no duplication observed |
| `scripts/playback_probe/flow/base.py` | 93 | Defines playback flow abstraction | script: business-logic | no duplication observed |
| `scripts/playback_probe/flow/registry.py` | 74 | Registers flow steps | script: business-logic | no duplication observed |
| `scripts/playback_probe/flow/steps/__init__.py` | 1 | Step package marker | script: support code | no duplication observed |
| `scripts/playback_probe/flow/steps/license.py` | 122 | Executes license step | script: business-logic | no duplication observed |
| `scripts/playback_probe/flow/steps/manifest.py` | 48 | Executes manifest step | script: business-logic | no duplication observed |
| `scripts/playback_probe/flow/steps/segments.py` | 72 | Executes segment step | script: business-logic | no duplication observed |
| `scripts/playback_probe/har_flow_parser.py` | 177 | Converts HAR into flow template | lib candidate: `har` | new duplication: `har_pinned_playbacks.py` |
| `scripts/playback_probe/har_pinned_playbacks.py` | 277 | Groups/pins HAR playback sessions | lib candidate: `har` | new duplication: `har_playback_grouping.py` |
| `scripts/playback_probe/har_playback_grouping.py` | 65 | Groups HAR playback entries | lib candidate: `har` | new duplication: `har_pinned_playbacks.py` |
| `scripts/playback_probe/har_probe_comparison_report.py` | 198 | Renders HAR/probe comparison | lib candidate: `report_render` | no duplication observed |
| `scripts/playback_probe/har_probe_comparison.py` | 219 | Compares HAR/probe data | script: business-logic | no duplication observed |
| `scripts/playback_probe/license_extractor.py` | 108 | Extracts license request data | lib candidate: `har` | new duplication: `ctap_har_extractor.py` |
| `scripts/playback_probe/logging_setup.py` | 84 | Configures probe logging | lib candidate: `paths` | new duplication: `applauseInvestigation/scripts/organize_reproduction_run.py` |
| `scripts/playback_probe/mpd_parser.py` | 263 | Parses MPEG-DASH MPD | script: business-logic | new duplication: `investigations/scripts/generate_drm_flow_report.py` |
| `scripts/playback_probe/session_builder.py` | 37 | Builds playback sessions | script: business-logic | no duplication observed |
| `scripts/playback_probe/timing.py` | 136 | Computes timing metrics | script: business-logic | new duplication: `mtn-network-traffic/scripts/curl_timer/curl_timing.py` |
| `scripts/populate_auth_from_curl.py` | 122 | Generates auth config from cURL | lib candidate: `curl_to_python`, `auth` | already cited: cURL converter |
| `scripts/populate_auth_from_har.py` | 121 | Generates auth config from HAR | lib candidate: `har`, `auth` | no duplication observed |
| `scripts/populate_ctap_auth_from_har.py` | 153 | Generates CTAP auth from HAR | lib candidate: `har`, `auth` | no duplication observed |
| `scripts/replay_license_request.py` | 159 | Replays license request | script: business-logic | no duplication observed |
| `scripts/run_full_flow.py` | 719 | Runs complete playback flow | script: business-logic | no duplication observed |
| `scripts/run_playback_probe.py` | 259 | CLI entry point for probe | script: business-logic | no duplication observed |
| `scripts/simulate_playsessions.py` | 168 | Simulates play sessions | script: business-logic | no duplication observed |
| `scripts/summarize_har_playbacks.py` | 151 | Summarizes HAR playback sessions | lib candidate: `har`, `report_render` | already cited: `summarize_har_playbacks.py::_load_entries()` |

Tests: `tests/flow/test_license_step.py` (175), `test_manifest_step.py` (72), `test_registry.py` (34), `test_segments_step.py` (97); `tests/lib/test_auth.py` (42), `test_build_distributable.py` (33),
`test_ctap_client.py` (139), `test_ctap_har_extractor.py` (48), `test_curl_parser.py` (122), `test_discover_content_ids.py` (158), `test_distributable_manifest.py` (74), `test_fcid.py` (16),
`test_fill_license_step_from_har.py` (163), `test_har_flow_parser.py` (101), `test_har_pinned_playbacks.py` (242), `test_har_playback_grouping.py` (62), `test_har_probe_comparison_report.py` (95),
`test_har_probe_comparison.py` (124), `test_license_extractor.py` (112), `test_mpd_parser.py` (135), `test_populate_auth_from_har.py` (68), `test_populate_ctap_auth_from_har.py` (110),
`test_run_full_flow.py` (544), `test_session_builder.py` (30), `test_simulate_playsessions.py` (117), `test_timing.py` (58). All are `script: test/support code`; no separate duplication.

**Rollup:** 65 files; source implementation is approximately 35 files. Approximately 12 source files are absorbable by existing `har`, `auth`, `curl_to_python`, `report_render`, or `paths`;
approximately 23 remain playback-specific. Extra work: likely a new `mpd`/DASH parsing module and possibly a playback-session/timing module. The current seven-module design does not cover those domain
mechanisms.

---

## 2. `mtn-zm-session-device-investigation`

**Purpose:** Runs a tenant-configured Athena pipeline that correlates session records, debug events, error codes, and device/session outcomes.

**Suggested category:** **investigation (recurring campaign)** — pipeline-style repeatable investigation with tenant/query registries and generated reports.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/athena_runner/investigation_config.py` | 143 | Investigation configuration | lib candidate: `paths` | no duplication observed |
| `scripts/athena_runner/queries/__init__.py` | 1 | Query package marker | lib candidate: `athena` | no duplication observed |
| `scripts/athena_runner/queries/base.py` | 51 | Athena query abstraction | lib candidate: `athena` | new duplication: `applauseInvestigation/run_athena_debug_events.py` |
| `scripts/athena_runner/queries/debug_events_by_session_ids.py` | 137 | Queries debug events by sessions | lib candidate: `athena` | new duplication: `run_athena_debug_events.py` |
| `scripts/athena_runner/queries/debug_events_lookup.py` | 75 | Looks up debug events | lib candidate: `athena` | new duplication: `debug_events_by_session_ids.py` |
| `scripts/athena_runner/queries/params.py` | 43 | Athena query parameters | lib candidate: `athena` | no duplication observed |
| `scripts/athena_runner/queries/registry.py` | 64 | Registers Athena queries | lib candidate: `athena` | no duplication observed |
| `scripts/athena_runner/queries/unified_sessions_lookup.py` | 97 | Queries unified sessions | lib candidate: `athena` | already cited: aws-access-cli/Athena runner pattern |
| `scripts/athena_runner/tenants.py` | 62 | Tenant registry/configuration | script: business-logic | new duplication: `shaka-6001-sa-error-analysis/scripts/lib/athena_runner.py` configuration |
| `scripts/athena_runner/time_window_utils.py` | 53 | Computes query windows | lib candidate: `paths` | new duplication: `applauseInvestigation/scripts/epoch_to_utc.py` |
| `scripts/build_final_session_report.py` | 167 | Joins classification/error CSVs | lib candidate: `csv_io`, `report_render` | new duplication: `scripts/summarize_final_session_report.py` |
| `scripts/classify_session_outcomes.py` | 152 | Classifies session outcomes | script: business-logic | no duplication observed |
| `scripts/extract_error_codes_from_debug_events.py` | 130 | Extracts error codes from event JSON | script: business-logic | no duplication observed |
| `scripts/extract_problematic_session_ids.py` | 80 | Selects problematic sessions | script: business-logic | no duplication observed |
| `scripts/generate_summary.py` | 125 | Generates investigation summary | lib candidate: `report_render` | new duplication: `applauseInvestigation` report scripts |
| `scripts/run_athena_query.py` | 345 | Athena query CLI | lib candidate: `athena` | new duplication: `shaka-6001-sa-error-analysis/scripts/lib/athena_runner.py` |
| `scripts/run_investigation_pipeline.py` | 499 | Orchestrates end-to-end pipeline | script: business-logic | no duplication observed |
| `scripts/summarize_final_session_report.py` | 104 | Summarizes final CSV | lib candidate: `csv_io`, `report_render` | new duplication: `build_final_session_report.py` |
| `scripts/verify_incomplete_no_destroy.py` | 138 | Verifies incomplete/no-destroy behavior | script: business-logic | no duplication observed |

Tests: 13 test files, 23–242 LOC each, covering the corresponding modules; all `script: test/support code`.

**Rollup:** 32 files; 19 implementation files and 13 tests. Approximately 10 implementation files fit existing `athena`, `csv_io`, `report_render`, and `paths`; approximately 9 are case-specific.
Extra work: tenant/query registry abstractions and session-outcome classification are materially beyond generic Athena execution.

---

## 3. `mtn-network-traffic`

**Purpose:** Measures HTTP/cURL timing and network-path diagnostics, including DNS, TLS, MTR, traceroute, WHOIS, JWT inspection, and Markdown reporting.

**Suggested category:** **tool**.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/curl_timer/blocks.py` | 57 | Timing-block model | lib candidate: `curl_to_python` | no duplication observed |
| `scripts/curl_timer/curl_timing.py` | 279 | Executes/parses cURL timings | lib candidate: `curl_to_python` | already cited: cURL converter |
| `scripts/curl_timer/dns_trace.py` | 117 | DNS diagnostics | script: business-logic | no duplication observed |
| `scripts/curl_timer/jwt_inspect.py` | 97 | Inspects JWT claims | script: business-logic | new duplication: `scripts/inspect_curl_auth.py` |
| `scripts/curl_timer/markdown_report.py` | 272 | Renders network report | lib candidate: `report_render` | new duplication: `mtn-network-traffic/scripts/curl_timer/report.py` |
| `scripts/curl_timer/mtr_probe.py` | 133 | Runs MTR probe | script: business-logic | no duplication observed |
| `scripts/curl_timer/report.py` | 317 | Aggregates probe report | lib candidate: `report_render` | new duplication: `markdown_report.py` |
| `scripts/curl_timer/tls_probe.py` | 80 | TLS diagnostics | script: business-logic | no duplication observed |
| `scripts/curl_timer/traceroute.py` | 127 | Traceroute diagnostics | script: business-logic | no duplication observed |
| `scripts/curl_timer/whois_lookup.py` | 106 | WHOIS lookup | script: business-logic | no duplication observed |
| `scripts/generate_timing_report.py` | 63 | Generates timing report | lib candidate: `report_render` | new duplication: `vod-playback-timing-probe/scripts/generate_timing_report.py` |
| `scripts/inspect_curl_auth.py` | 80 | Inspects cURL authentication | lib candidate: `curl_to_python`, `auth` | new duplication: `curl_timer/jwt_inspect.py` |
| `scripts/time_curl_requests.py` | 248 | Times cURL requests | lib candidate: `curl_to_python` | already cited: cURL converter |

Tests: 9 test files, 51–120 LOC, covering network diagnostics; `script: test/support code`.

**Rollup:** 22 files; 13 implementation files and 9 tests. Approximately 6 implementation files fit existing `curl_to_python`/`report_render`/`auth`; approximately 7 remain
network-diagnostic-specific. Extra work: a genuinely new network diagnostics module would be needed if this tool is migrated.

---

## 4. `vod-asset-ingestion-mapping`

**Purpose:** Recurring MTN SA investigation tracing VOD assets from OpsHub ADI ingestion through Mongo/CTAP/display and Lightstep, cross-checked with HAR captures.

**Suggested category:** **investigation (recurring campaign)**. README explicitly describes it as a “continuous data-gathering exercise.”

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/analyze_provider_asset_counts.py` | 103 | Counts provider assets | script: business-logic | no duplication observed |
| `scripts/build_common_field_mapping.py` | 292 | Builds cross-system field map | script: business-logic | no duplication observed |
| `scripts/extract_har_json.py` | 64 | Extracts JSON bodies from HAR | lib candidate: `har` | new duplication: `vod-playback-timing-probe/scripts/playback_probe/ctap_har_extractor.py` |
| `scripts/extract_lightstep_trace_fields.py` | 51 | Extracts Lightstep fields | script: business-logic | new duplication: `scripts/lib/lightstep_trace.py` |
| `scripts/lib/adi_parser.py` | 136 | Parses ADI XML | script: business-logic | no duplication observed |
| `scripts/lib/har_parser.py` | 70 | Loads HAR entries | lib candidate: `har` | already cited: `har_parser.py::load_json_entries()` |
| `scripts/lib/id_components.py` | 54 | Parses asset IDs | script: business-logic | no duplication observed |
| `scripts/lib/json_response.py` | 34 | Handles response JSON | lib candidate: `har` | new duplication: `extract_har_json.py` |
| `scripts/lib/lightstep_trace.py` | 61 | Parses Lightstep trace data | script: business-logic | new duplication: `extract_lightstep_trace_fields.py` |
| `scripts/lib/opshub_csv.py` | 119 | Parses OpsHub CSV values | lib candidate: `csv_io` | new duplication: `mtn-zm-session-device-investigation/scripts/build_final_session_report.py` |
| `scripts/lib/value_index.py` | 104 | Builds value indexes | script: business-logic | no duplication observed |
| `scripts/map_har_fields.py` | 117 | Maps ADI fields to HAR fields | script: business-logic | no duplication observed |
| `scripts/map_har_to_opshub_adi.py` | 146 | Correlates HAR and ADI | script: business-logic | no duplication observed |
| `scripts/map_opshub_adi_fields.py` | 190 | Maps OpsHub/ADI fields | script: business-logic | no duplication observed |

**Rollup:** 15 files; 4 clear existing-lib candidates and 11 project-specific scripts. Extra work: ADI XML parsing, Lightstep trace parsing, and asset-ID/value-correlation helpers are new
shared-module candidates only if another ingestion project appears.

---

## 5. Root `investigations`

**Purpose:** Small collection of investigation utilities for player/session checks, Jira/search extraction, DRM-flow reporting, and JWS signing.

**Suggested category:** **investigation (bounded case)**, with some generic utilities.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/check_bein.py` | 46 | Checks beIN-related data | script: business-logic | no duplication observed |
| `scripts/check_player_version.py` | 82 | Checks player versions | script: business-logic | no duplication observed |
| `scripts/check_session.py` | 39 | Checks session data | script: business-logic | no duplication observed |
| `scripts/extract_comments_bulk.py` | 57 | Extracts comments in bulk | script: business-logic | no duplication observed |
| `scripts/extract_jira.py` | 45 | Extracts Jira information | script: business-logic | new duplication: `extract_jira2.py` |
| `scripts/extract_jira2.py` | 75 | Alternate Jira extractor | script: business-logic | new duplication: `extract_jira.py` |
| `scripts/extract_search.py` | 54 | Extracts search results | script: business-logic | no duplication observed |
| `scripts/generate_drm_flow_report.py` | 230 | Generates DRM flow report | script: business-logic | new duplication: `vod-playback-timing-probe/scripts/playback_probe/mpd_parser.py` |
| `scripts/get_final_answer.py` | 24 | Formats investigation answer | lib candidate: `report_render` | no duplication observed |
| `scripts/sign_jws_json.py` | 74 | Signs JSON as JWS | script: business-logic | no duplication observed |

**Rollup:** 10 files; 1 report-render candidate and 9 local scripts. No required new shared module, although DRM/MPD parsing overlaps the playback tool.

---

## 6. `applauseInvestigation`

**Purpose:** Analyzes Applause issue exports, Lightstep CSVs, Athena playback/debug-event data, and HAR captures, and organizes reproduction artifacts.

**Suggested category:** **investigation (recurring campaign)**.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/analyze_applause_issues.py` | 156 | Loads/summarizes issue CSV exports | lib candidate: `csv_io` | new duplication: `astro-events-household-report/scripts/inspect_sample_keys.py` |
| `scripts/analyze_athena_playback.py` | 440 | Analyzes Athena playback CSVs | lib candidate: `athena`, `csv_io` | already cited in src-lib migration |
| `scripts/analyze_har.py` | 270 | Analyzes HAR capture | lib candidate: `har` | already cited: `analyze_har.py::iter_entries()` |
| `scripts/analyze_lightstep_big_picture.py` | 160 | Analyzes Lightstep big-picture CSV | lib candidate: `csv_io`, `report_render` | new duplication: `analyze_lightstep_latency.py` |
| `scripts/analyze_lightstep_latency.py` | 181 | Analyzes Lightstep latency CSV | lib candidate: `csv_io`, `report_render` | new duplication: `analyze_lightstep_big_picture.py` |
| `scripts/analyze_smvod_sessions.py` | 101 | Analyzes SM-VOD session CSV | lib candidate: `csv_io` | already cited: `analyze_athena_playback.py` CSV pattern |
| `scripts/epoch_to_utc.py` | 32 | Converts epoch timestamps | lib candidate: `paths` | new duplication: `mtn-zm.../time_window_utils.py` |
| `scripts/organize_reproduction_run.py` | 164 | Organizes HAR/log/video artifacts | lib candidate: `paths`, `report_render` | new duplication: `vod-playback-timing-probe/logging_setup.py` |
| `scripts/run_athena_debug_events.py` | 276 | Runs Athena debug-event query | lib candidate: `athena` | new duplication: `mtn-zm.../queries/debug_events_by_session_ids.py` |

**Rollup:** 9 files; approximately 8 lib candidates and 1 business-logic analyzer. Extra work: none required beyond planned modules.

---

## 7. `shaka-6001-sa-error-analysis`

**Purpose:** Queries and analyzes daily/session Shaka playback errors for South Africa.

**Suggested category:** **investigation (recurring campaign)**.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/lib/athena_runner.py` | 108 | Athena execution helper | lib candidate: `athena` | new duplication: `mtn-zm.../scripts/run_athena_query.py` |
| `scripts/lib/aws_sso.py` | 108 | AWS SSO credential refresh | lib candidate: `auth` | already cited: `aws-access-cli/scripts/refresh_aws_sso.py` |
| `scripts/lib/user_agent_parser.py` | 61 | Parses device/user-agent data | script: business-logic | new duplication: `mtn-zm.../tenants.py` only at configuration boundary |
| `scripts/query_daily_shaka_errors.py` | 238 | Queries daily Shaka errors | script: business-logic | no duplication observed |
| `scripts/query_session_shaka_errors.py` | 185 | Queries session Shaka errors | script: business-logic | no duplication observed |

**Rollup:** 6 files including package marker; 2 existing-lib candidates and 3 local implementations. No required new module; user-agent/device parsing could become a future `device_identity` module.

---

## 8. Root `scripts`

**Purpose:** Repository maintenance and knowledge/report-generation utilities.

**Suggested category:** **tool**.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `disk_usage.py` | 165 | Reports directory disk usage | script: business-logic | no duplication observed |
| `generate_scripts_registry.py` | 138 | Generates script registry | script: business-logic | no duplication observed |
| `reflow_markdown.py` | 143 | Reflows Markdown text | script: business-logic | no duplication observed |
| `update_athena_table_ddl_knowledge.py` | 131 | Updates Athena DDL knowledge document | lib candidate: `csv_io`, `report_render` | new duplication: `mtn-zm.../generate_summary.py` |

**Rollup:** 4 files; 1 existing-lib candidate and 3 repository-specific maintenance tools.

---

## 9. `astro-events-household-report`

**Purpose:** Inspects sample Astro event/household CSV keys and pivots distinct-value exports.

**Suggested category:** **investigation (bounded case)**.

| File | LOC | Purpose | Classification | Duplication |
|---|---:|---|---|---|
| `scripts/inspect_sample_keys.py` | 40 | Inspects join-key consistency | lib candidate: `csv_io` | new duplication: `applauseInvestigation/scripts/analyze_applause_issues.py` |
| `scripts/pivot_distinct_values.py` | 56 | Pivots distinct-value CSV | lib candidate: `csv_io` | new duplication: `mtn-zm.../build_final_session_report.py` |

**Rollup:** 2 files; both are absorbable by `csv_io`; no new module required.

---

## 10. `smarttv-mtntv`

**Purpose:** Signs JSON payloads for SmartTV/MTN TV requests.

**Suggested category:** **tool**.

| File | LOC | Purpose | Classification | Duplication |
|---:|---:|---|---|---|
| `scripts/signedJson.py` | 50 | Creates signed JSON payload | script: business-logic | no duplication observed |

**Rollup:** 1 file; 1 local script. A future cryptographic signing/auth module is possible, but it is not one of the seven currently scoped modules.

---

# Cross-cutting duplication clusters

These are additional clusters not already listed in the existing `src-lib-migration` evidence.

## HAR and request extraction

- `vod-playback-timing-probe/scripts/playback_probe/ctap_har_extractor.py`
- `vod-playback-timing-probe/scripts/playback_probe/license_extractor.py`
- `vod-playback-timing-probe/scripts/playback_probe/har_flow_parser.py`
- `vod-playback-timing-probe/scripts/playback_probe/har_pinned_playbacks.py`
- `vod-playback-timing-probe/scripts/playback_probe/har_playback_grouping.py`
- `vod-asset-ingestion-mapping/scripts/extract_har_json.py`
- `vod-asset-ingestion-mapping/scripts/lib/json_response.py`

These are partly absorbable by `har`, but flow extraction, playback grouping, and license selection are materially domain-specific extensions.

## Athena execution and debug-event querying

- `mtn-zm-session-device-investigation/scripts/run_athena_query.py`
- `mtn-zm-session-device-investigation/scripts/athena_runner/queries/base.py`
- `mtn-zm-session-device-investigation/scripts/athena_runner/queries/debug_events_by_session_ids.py`
- `mtn-zm-session-device-investigation/scripts/athena_runner/queries/debug_events_lookup.py`
- `applauseInvestigation/scripts/run_athena_debug_events.py`
- `shaka-6001-sa-error-analysis/scripts/lib/athena_runner.py`

The generic execution/wait/download layer fits `athena`; query-specific classes and event schemas remain local unless the Athena module intentionally supports a query registry.

## CSV joins and summaries

- `mtn-zm-session-device-investigation/scripts/build_final_session_report.py`
- `mtn-zm-session-device-investigation/scripts/summarize_final_session_report.py`
- `vod-asset-ingestion-mapping/scripts/lib/opshub_csv.py`
- `astro-events-household-report/scripts/inspect_sample_keys.py`
- `astro-events-household-report/scripts/pivot_distinct_values.py`
- `applauseInvestigation/scripts/analyze_applause_issues.py`

Generic loading/validation belongs in `csv_io`; field selection, error-code ranking, household joins, and OpsHub semantics remain project-specific.

## Report rendering

- `mtn-network-traffic/scripts/curl_timer/markdown_report.py`
- `mtn-network-traffic/scripts/curl_timer/report.py`
- `mtn-network-traffic/scripts/generate_timing_report.py`
- `vod-playback-timing-probe/scripts/generate_timing_report.py`
- `vod-playback-timing-probe/scripts/playback_probe/har_probe_comparison_report.py`
- `mtn-zm-session-device-investigation/scripts/generate_summary.py`
- `scripts/update_athena_table_ddl_knowledge.py`

The output-format helpers fit `report_render`; report semantics do not.

## Time and authentication helpers

- `applauseInvestigation/scripts/epoch_to_utc.py`
- `mtn-zm-session-device-investigation/scripts/athena_runner/time_window_utils.py`
- `vod-playback-timing-probe/scripts/playback_probe/auth.py`
- `vod-playback-timing-probe/scripts/populate_auth_from_har.py`
- `vod-playback-timing-probe/scripts/populate_ctap_auth_from_har.py`
- `mtn-network-traffic/scripts/inspect_curl_auth.py`
- `mtn-network-traffic/scripts/curl_timer/jwt_inspect.py`

Auth credential extraction fits `auth`; JWT inspection and playback-specific auth configuration do not necessarily fit the current protocol.

---

# Rough aggregate estimate

Using the requested ~166-file scope, including tests:

| Bucket | Rough count | Interpretation |
|---|---:|---|
| Existing seven modules can absorb directly | **~35-45 files** | Athena runners, HAR loaders, cURL parsing, CSV load/write, report rendering, SSO, path/logging helpers. Tests not counted. |
| Irreducible project-specific business logic | **~95-105 files** | Playback flow, session-outcome classification, Shaka error analysis, OpsHub/ADI correlation, network probes, DRM/MPD semantics. |
| Suggest a genuinely new shared module | **~15-25 files, overlaps bucket 2** | Candidates: `mpd`/DASH parsing, timing correlation, network diagnostics, ADI/XML mapping, UA identity, crypto signing. |

The largest realistic migration gain comes from `applauseInvestigation`, the Athena portions of `mtn-zm-session-device-investigation`, HAR handling in `vod-playback-timing-probe`, cURL handling in
`mtn-network-traffic`, and CSV utilities in `astro-events-household-report`. The remaining scripts encode campaign-specific decisions and should remain under project taxonomy folders rather than being
forced into `src/lib/`.