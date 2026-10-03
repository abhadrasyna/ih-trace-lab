# CTAP/SM-VOD script audit

This audit applies `docs/guides/functional-code-taxonomy.md`'s shared-vs-specific test per file: domain-mechanism code that stays the same across unrelated consumers is **lib**; campaign-specific
merge, analysis, orchestration, and parsing rules are **script**.

## Scripts inventory (`scripts/`)

| File | LOC | Verdict | FCT-1 test result | Needs `src/lib/*` |
|---|---:|---|---|---|
| `analyze_api_timing.py` | 291 | script | Reads an exported API-timing workbook and emits CTAP/SM-VOD-specific summaries; the analysis rule is business logic, not shared infrastructure. | `csv_io` |
| `analyze_debug_sample.py` | 55 | script | Inspects one campaign's sampled debug-event export; the anomaly interpretation is investigation-specific. | `csv_io` |
| `analyze_errorcode_correlation.py` | 150 | script | Correlates this campaign's position/error reports across dates; correlation rules are business logic, not reusable infrastructure. | `csv_io` |
| `analyze_outcome_report.py` | 487 | script | Computes campaign-specific playback-outcome slices and diagnostics from merged reports; the rules answer this investigation's question. | `csv_io` |
| `analyze_session_guard_net_latency.py` | 161 | script | Examines one exported latency dataset with investigation-specific thresholds and views. | `csv_io` |
| `analyze_webview_devices.py` | 230 | script | Classifies WebView-device behavior for this campaign's merged report; classification rules stay local. | `csv_io` |
| `analyze_wv_device_cross_date_success.py` | 152 | script | Cross-date success tracking over CTAP/SM-VOD reports is campaign-specific aggregation logic. | `csv_io` |
| `analyze_wv_failure_then_success_devices.py` | 193 | script | Detects this campaign's failure-then-success device pattern; the rule is business logic. | `csv_io` |
| `build_debug_completeness_query.py` | 93 | script | Builds a CTAP/SM-VOD-specific query from investigation inputs; the query shape stays local. | `csv_io`, later `query-catalog` |
| `build_mtn_summary.py` | 113 | script | Produces an MTN-focused summary derived from this investigation's outputs; summarization rules are local business logic. | `csv_io` |
| `build_webview_device_summary.py` | 162 | script | Builds a WebView-device summary tailored to this campaign's output fields and questions. | `csv_io` |
| `correlate_cdn_ips.py` | 456 | script | Joins campaign-specific session outputs with CDN correlation evidence; the join semantics are investigation logic. | `csv_io` |
| `extract_position_report.py` | 140 | script | Extracts a position-check view defined by this campaign's error/lifecycle interpretation. | `csv_io` |
| `extract_session_ids.py` | 81 | script | Pulls the session-id subset needed by the CTAP/SM-VOD Athena/debug workflow; the selection is campaign-specific. | `csv_io` |
| `extract_session_timeline.py` | 58 | script | Reshapes one session export into a timeline for this investigation's exploration flow. | `csv_io` |
| `filter_error_code_report.py` | 73 | script | Concatenates campaign-specific position reports for one error code/range; the derived artifact is local business logic. | `csv_io` |
| `flatten_debug_events.py` | 72 | script | Streams one campaign's debug-event export through a local parser to produce a flattened investigation artifact. | `csv_io` |
| `lib/__init__.py` | 0 | script | Package marker only; no shared mechanism is implemented here. | none |
| `lib/athena_runner.py` | 108 | lib | Starts, polls, and downloads Athena queries: a pure domain mechanism reused by unrelated projects, now superseded by `src/lib/athena`. | superseded by `athena` |
| `lib/aws_sso.py` | 111 | lib | Ensures AWS SSO credentials are valid: shared auth/bootstrap mechanism, now superseded by `src/lib/auth`. | superseded by `auth` |
| `lib/debug_event_parser.py` | 276 | script | Parses one campaign's debug-event row shape and event semantics; this is CTAP/SM-VOD-specific business logic, not a generic JSON/CSV mechanism. | none |
| `lightstep_ctap_smvod_join.py` | 325 | script | Combines CTAP and SM-VOD manual exports using campaign-specific join and labeling rules. | `csv_io` |
| `merge_ctap_smvod_csv.py` | 363 | script | Performs the campaign's core 3-way merge and derived-column logic; that logic stays local even though file I/O should move to `csv_io`. | `csv_io` |
| `merge_session_outcome.py` | 509 | script | Enriches the merged CTAP/SM-VOD report with Athena/debug outcomes using campaign-specific rules. | `csv_io` |
| `parse_debug_user_agents.py` | 243 | script | Parses/debug-classifies user-agent strings only in the context of this investigation's output needs. | `csv_io` |
| `process_traces.py` | 239 | script | Reshapes trace exports into this campaign's investigation-specific CSV evidence. | `csv_io` |
| `run_athena_debug_events.py` | 190 | script | Campaign-specific Athena consumer; auth/query execution is shared, but the chosen query and artifact are local rules. | `auth`, `athena`, `csv_io` |
| `run_athena_playback_outcome.py` | 149 | script | Same split as above: campaign-specific Athena enrichment step over shared auth/query/csv mechanisms. | `auth`, `athena`, `csv_io` |
| `run_pipeline.py` | 213 | script | Orchestrates this campaign's six-step workflow, including the manual Lightstep export step. | `auth`, `athena`, `csv_io` |

## `queries/` inventory for CSM-6

These 45 files are not classified lib-vs-script here. They are query/catalog artifacts handed to CSM-6, which will move the reusable query text into the repo's root `queries/` catalog and leave
exploration evidence/story notes outside executable script ownership.

```text
.DS_Store
QUERY_CATALOG.md
adoption.md
athena_session_outcome.md
backups/04_position_tracking_pre_app_keepalive_13072026.md
backups/BLUEPRINT_pre_app_keepalive_13072026.md
backups/QUERY_CATALOG_pre_app_keepalive_13072026.md
edge_4032_playback_failure.md
exploration/.DS_Store
exploration/01_show_create_table.md
exploration/02_sample_rows.md
exploration/03_unified_sessions_ddl.md
exploration/04_position_tracking.md
exploration/6001_debug_error_aug.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/e6auj7k7_ccl_debug_events.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/e6auj7k7_ccl_debug_events_flat.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/fact_navigation_interactions.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/fact_navigation_journeys.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/fact_navigation_steps.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/fact_navigation_to_features.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/fact_sessions.csv
exploration/TKNYHrQtUYwr8aHyC2boBiBALmzWJm2MAew2zgYJtBb7Q_Gcr6v1/unified_sessions.csv
exploration/api-timing.xlsx
exploration/api_timing_client_probe_1RxJQnAJ3_23092026.md
exploration/b2255524.csv
exploration/check_version.csv
exploration/content_id_empty.csv
exploration/ctap_route_latency_p95_R-K52xrOoH0CQ5.csv
exploration/debug_event.csv
exploration/errorcode_3016_raw_08012026_08312026.csv
exploration/errorcode_E31012_1003_household_overlap_08012026_08312026.csv
exploration/errorcode_E31012_household_daywise_08012026_08312026.csv
exploration/errorcodes.csv
exploration/jira_ticket_household_net_latency_R-K52xrOoH0CQ5.md
exploration/new_player_error.csv
exploration/playing_no_play_debug_check.sql
exploration/playing_sessionid.csv
exploration/session_guard_latency_p95_R-K52xrOoH0CQ5.csv
exploration/session_guard_net_latency_R-K52xrOoH0CQ5.csv
stories/01_the_tables.md
stories/02_finding_the_outcome_field.md
stories/03_lifecycle_fingerprint_and_position.md
stories/04_the_missing_sessions_mystery.md
stories/05_devices_errors_and_new_territory.md
stories/README.md
```
