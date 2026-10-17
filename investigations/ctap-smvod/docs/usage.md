# CTAP/SM-VOD script usage

All commands run from `investigations/ctap-smvod/scripts/`. Dates are `DDMMYYYY` unless noted. Inputs and outputs are namespaced per tenant: outputs go to `../output/<TENANT>/` (per-date files are
prefixed `YYYY-MM-DD_`), Lightstep exports are read from `../data/lightstep/<TENANT>/`, Athena pulls go to `../data/athena/<TENANT>/`. Tenant codes come from `config/tenants.yaml` (`SA`, `NG`, `ZM`,
`GH`); paths below that omit `<TENANT>/` for brevity are always under the tenant folder.

## 0. Multi-tenant model

```bash
python3 run_pipeline.py --date 06102026                # every tenant that has Lightstep input for the date
python3 run_pipeline.py --date 06102026 --tenant ZM    # one tenant only
python3 summarize_pipeline_run.py --date 06102026 --tenant ZM   # reconcile export row counts vs the merged report
python3 summarize_tenant_status.py --date 06102026              # SA,GH,ZM status table (UTC day) -> docs/2026-10-06-tenant-status-summary.md (--tenants, --out, --force)
```

- With no `--tenant`, tenants with no `data/lightstep/<TENANT>/` input for the date are skipped. Within a tenant the pipeline stops at the first failing step; other tenants still run, a per-tenant
  summary prints, and the exit code is non-zero if any tenant failed.
- An unknown tenant, or a missing input folder, fails with a message naming the expected path.
- Standalone scripts (Steps 6b/6e/6d, ranges, rollups) take `--output-dir` / `--input-dir`; pass `../output/<TENANT>` explicitly, e.g. `python3 extract_error_report_1xxx_6xxx.py --from 01102026 --to
  06102026 --output-dir ../output/SA`.

### Per-tenant Lightstep export rule

Export the ctap, smvod and smvod-ts files for the date into `data/lightstep/<TENANT>/`. For a tenant on a **shared** Lightstep project (`shared_project: true` in `config/tenants.yaml`, currently ZM
and GH on `mcs-go-prod-mtn-1-eu`), the Lightstep query must filter on the tenant's `busUnitId` (its `go_id`) and group by it, so the merge can verify no other tenant's rows are present:

| Export | Filter / group-by attribute |
|---|---|
| ctap | `sessionInfo.busUnitId` |
| smvod (sm-vod service) | `busUnitId` (no `sessionInfo.` prefix) |

Step 2 (`merge_ctap_smvod_csv.py`) fails loudly if any row is blank, mismatched, or the column is missing. Dedicated-project tenants (SA, NG) need no `busUnitId` filter.

### Adding a tenant

1. Add the opco to `config/tenants.yaml` (resolve identifiers via `scripts/resolve_tenant.py`; see `docs/guides/tenant-resolution.md`).
2. Create `data/lightstep/<TENANT>/` and drop the exports in (with the `busUnitId` filter above if the project is shared).
3. Run `run_pipeline.py --date <d> --tenant <TENANT>` (Athena steps use the registry's tenant id, profile and region), then `summarize_pipeline_run.py` to reconcile counts.

## 1. Full pipeline (one date)

```bash
python3 run_pipeline.py --date 06102026
```

Prerequisite: the Lightstep exports for the date already sit in `data/lightstep/` (`YYYY-MM-DD_ctap.csv`, `YYYY-MM-DD_smvod.csv`, optional `YYYY-MM-DD_smvod-ts.csv`). Step 1 is manual.

| Step | Script | Writes |
|---|---|---|
| 1b | `combine_lightstep_parts.py` | `data/lightstep/YYYY-MM-DD_{ctap,smvod,smvod-ts}.csv` (only if numbered `_01_` parts exist) |
| 2 | `merge_ctap_smvod_csv.py` | `output/YYYY-MM-DD_setupsession.csv` |
| 3 | `run_athena_playback_outcome.py` | `data/athena/YYYY-MM-DD_session.csv` |
| 4 | `run_athena_debug_events.py` | `data/athena/YYYY-MM-DD_debug_states.csv` |
| 5 | `merge_session_outcome.py` | `output/YYYY-MM-DD_setupsession_with_outcome.csv` (the full report; source for everything below) |
| 6b | `extract_position_report.py` | `output/YYYY-MM-DD_position_report.csv` |
| 6e | `extract_error_report_1xxx_6xxx.py` | `output/YYYY-MM-DD_error_report_1xxx_6xxx.csv` |
| 6d | `analyze_webview_devices.py` | `output/YYYY-MM-DD_webview_device_report.csv` |
| 6f | `run_athena_error_eventdata.py` | `data/athena/YYYY-MM-DD_error_eventdata.csv` (raw `PLAYER_ERROR` eventdata) |
| 6g | `flatten_error_eventdata.py` | `output/<T>/error_eventdata_flat/<date>_all.csv` + `<date>_<errorcode>.csv` per code |

Variations:

```bash
python3 run_pipeline.py --date 06102026 --dry-run                    # print commands only, touch nothing
python3 run_pipeline.py --date 06102026 --skip-step3 --skip-step4    # reuse existing Athena CSVs
python3 run_pipeline.py --date 06102026 --skip-if-exists             # skip Athena per step only if its CSV exists
python3 run_pipeline.py --date 06102026 --skip-step6b                # no position_report.csv
python3 run_pipeline.py --date 06102026 --skip-step6e                # no 1xxx/6xxx error report
python3 run_pipeline.py --date 06102026 --skip-step6d                # no webview device report
python3 run_pipeline.py --date 06102026 --skip-error-eventdata       # no raw error eventdata export + flatten (Steps 6f/6g)
python3 run_pipeline.py --date 06102026 --full-position-report       # position_report.csv with ALL sessions (needed for Steps 6c/7)
python3 run_pipeline.py --date 06102026 --profile <aws-sso-profile> --skip-auth-check   # Athena auth passthrough (Steps 3/4)
```

The pipeline is per-date only; for a range, loop over dates or use the range-capable scripts below.

## 2. Position report (`extract_position_report.py`)

```bash
python3 extract_position_report.py --date 06102026                       # only position_not_moved == true (default)
python3 extract_position_report.py --date 06102026 --no-only-not-moved   # every session
python3 extract_position_report.py --date 06102026 --error-code 1003     # only sessions containing code 1001-1010
python3 extract_position_report.py --date 06102026 --columns sessionId,error_codes --out /tmp/x.csv
```

Writes `output/YYYY-MM-DD_position_report.csv` (or `--out`). Columns: householdId, deviceId, session.clientIp, sessionId, content_uuid, start_time, error_codes, error_descriptions, state_sequence,
min_position, max_position, position_not_moved. Other options: `--input`.

## 3. 1xxx/6xxx error report (`extract_error_report_1xxx_6xxx.py`)

Same columns as the position report plus `is_wv` (`true` when the user agent has the `; wv` token, `false` when a UA is present without it, blank when none), but from the full
`setupsession_with_outcome.csv` and filtered to sessions with an exact 4-digit `error_codes` token starting with 1 or 6 (e.g. 1003, 6001; not 3016 or E31012). Not limited to position_not_moved. Reads
existing files only (never calls Athena) and aborts listing any missing dates.

```bash
python3 extract_error_report_1xxx_6xxx.py --date 06102026                          # one CSV
python3 extract_error_report_1xxx_6xxx.py --from 01102026 --to 06102026           # one XLSX, one sheet per date
python3 extract_error_report_1xxx_6xxx.py --date 06102026 --out /tmp/e.csv --columns sessionId,error_codes
python3 extract_error_report_1xxx.py --from 01102026 --to 06102026                 # 1xxx only, SA,GH,ZM at once: one XLSX per tenant in output/<TENANT>/ (--tenants, --output-dir ROOT)
python3 combine_error_report_1xxx_csv.py --tenant SA --from 01102026 --to 11102026 # 1xxx, ONE tenant, ONE CSV (leading `date` column): output/SA/<range>_error_report_1xxx_combined.csv
python3 rank_households_by_error.py --xlsx ../output/SA/2026-10-01_2026-10-13_error_report_1xxx.xlsx --top 25  # households by error sessions
```

| Mode | Output |
|---|---|
| `--date D` | `output/YYYY-MM-DD_error_report_1xxx_6xxx.csv` |
| `--from A --to B` | `output/A_B_error_report_1xxx_6xxx.xlsx` (ISO dates; sheets named `YYYY-MM-DD`) |

Other options: `--output-dir`. `rank_households_by_error.py` also reports days, devices and error codes per household and writes the full ranking to `<xlsx stem>_household_ranking.csv` (`--out-dir`).

### Combine per-error-code files across opcos (`combine_error_code_by_opco.py`)

Merges the `output/<TENANT>/error_eventdata_flat/<date>_<errorcode>.csv` files (the `_all.csv` files are ignored) into **one XLSX per error code** (flattened columns differ by code, so codes are never
mixed): one sheet per opco, all dates stacked, with a leading `date` column. An opco with no rows for a code gets no sheet. Tenants are auto-discovered; the date range and `--codes` are optional (omit
them for every date and code found). Reads existing files only.

```bash
python3 combine_error_code_by_opco.py --from 08102026 --to 11102026   # -> output/error_code/<code>/2026-10-08_2026-10-11_error_<code>_by_opco.xlsx per code
python3 combine_error_code_by_opco.py --codes 6007,1003                # all dates -> output/error_code/6007/all_dates_error_6007_by_opco.xlsx, output/error_code/1003/...
```

Other options: `--output-dir` (root holding the `<TENANT>/` folders).

## 4. Per-date and range analysis

| Command | Writes |
|---|---|
| `python3 analyze_webview_devices.py --date 18092026` | `output/YYYY-MM-DD_webview_device_report.csv` |
| `python3 analyze_webview_devices.py --start-date 2026-09-01 --end-date 2026-09-10` | one `YYYY-MM-DD_webview_device_report.csv` per date (range uses ISO dates) |
| `python3 analyze_error_report_breakdown.py --error-report ../output/SA/2026-10-09_error_report_1xxx_6xxx.csv [--outcome-report ...]` | stdout only (error code / `is_wv` / device / hour breakdown) |
| `python3 analyze_error_report_breakdown.py --all-codes --error-report ../output/ZM/2026-10-04_setupsession_with_outcome.csv` | same breakdown over every error code (incl. 3016) |
| `python3 flatten_error_eventdata.py --input <export>.csv --date <date> --out-dir ../output/ZM/error_eventdata_flat` | `<date>_all.csv`: `eventdata` split into columns + `raw_eventdata` |
| `python3 flatten_error_eventdata.py ... --split-by-errorcode` | also `<date>_<errorcode>.csv` per code, columns blank for that code dropped |
| `python3 summarize_error_eventdata.py --flat <flat>.csv --by errorcode,net_effectivetype` | stdout only (counts/crosstab over flat columns; `--by` repeatable) |
| `python3 count_error_by_content.py --from 2026-10-01 --to 2026-10-10 --tenants SA` | `output/<TENANT>/<from>_<to>_error_6xxx_by_content[_rollup].csv` (`sessions,unique_households`) |
| `python3 compute_concurrent_playback.py --date 2026-10-14 --tenants SA,GH,ZM` | `output/<TENANT>/<date>_concurrent_playback[_summary].csv` (per UTC minute, three views); see note below |
| `python3 chart_concurrent_playback.py --date 2026-10-14 --tenants SA,GH,ZM` | `output/<TENANT>/<date>_concurrent_playback.png` (run compute first; a chart failure is logged, CSVs stay) |
| `python3 chart_playback_attempts.py --date 2026-10-14 --tenants SA,GH,ZM [--bucket-min 5]` | `output/<TENANT>/<date>_playback_attempts.png` (unique-session attempts per bucket) |
<!-- lint-ignore-length -->
| `python3 run_athena_session_ingest.py --date 2026-10-14 --tenant SA` | `data/athena/<TENANT>/<date>_session_ingest.csv` (`sessionId,event_start,ingest_timestamp`, partitions D-1 and D; catalog `ctap-smvod-session-ingest`) |
<!-- lint-ignore-length -->
| `python3 chart_playback_attempts.py --date 2026-10-14 --tenants SA --time-field ingest` | `output/<TENANT>/<date>_playback_attempts_ingest.png` (attempts at each session's earliest `ingest_timestamp`; run the export first; sessions that started that day but landed on another are counted in the title) |
<!-- lint-ignore-length -->
| `python3 compare_lightstep_athena_sessions.py --date 2026-10-14 --tenant SA` | stdout counts (both / Lightstep-only / Athena-only) + `output/<TENANT>/<date>_lightstep_vs_athena_sessions.csv` (one row per one-sided session; Lightstep side = `setupsession.csv`, Athena side = `data/athena/<T>/<date>_session.csv`, enriched from `_session_ingest.csv` when present) |
<!-- lint-ignore-length -->
| `python3 run_athena_debug_sessions.py --date 2026-10-14 --tenant SA [--table-suffix sept26]` | `data/athena/<TENANT>/<date>_debug_sessions.csv` (`sessionId,first_event`: distinct `abr-vod-` sessions with a PLAYER_SESSION_EVENT/STATE_CHANGE/ERROR in the UTC day; catalog `ctap-smvod-debug-sessions`) |
<!-- lint-ignore-length -->
| `python3 compare_lightstep_athena_sessions.py --date 2026-10-14 --tenant SA --debug` | as above plus the debug-events set: per-region counts (L/U/D Venn) on stdout and an `in_debug` column in the mismatch CSV |
| `python3 find_codec_support_content.py --from 2026-10-01 --to 2026-10-11 --tenant SA --codec ec-3` | `output/<TENANT>/<from>_<to>_ec-3_true_by_content[_sessions\|_split].csv` |
| `python3 analyze_wv_device_cross_date_success.py --date 18092026` | `output/YYYY-MM-DD_wv_device_cross_date_history.csv` |
| `python3 analyze_wv_failure_then_success_devices.py` | `output/wv_failure_then_success_report_rollup.csv`, `output/wv_failure_then_success_evidence_rollup.csv` |
| `python3 build_webview_device_summary.py` | `output/webview_device_summary_report_rollup.csv` (from all `*_webview_device_report.csv`) |
| `python3 analyze_outcome_report.py --date 18092026 [--out report.md]` | markdown to stdout, or `--out` file |

Concurrent playback: `compute_concurrent_playback.py` reads `output/<TENANT>/<date>_setupsession_with_outcome.csv` plus `data/athena/<TENANT>/<date>_session.csv` and `_debug_states.csv`, and counts
distinct sessions per UTC minute. `csv_only` and `athena_exact` use only sessions with both `event_start` and `event_end` (a lower bound). `athena_estimated` also uses the first and last debug event
of sessions with no `event_end`; that last event is an estimate of the end, not a real stop, and sessions with no debug events are counted as unresolved in `..._summary.csv`.

## 5. Error-code filtering and CDN correlation (need the FULL position report)

Run `run_pipeline.py ... --full-position-report` (or `extract_position_report.py --no-only-not-moved`) first.

```bash
# several dates -> one CSV of one error code (default 1003)
python3 filter_error_code_report.py --dates 02082026,03082026 --error-code 1003

# join with the CDN team export
python3 correlate_cdn_ips.py --date 06102026 [--cdn-file F] [--position-report P] [--out O] [--escalation-out E]

# roll up all escalation files
python3 build_mtn_summary.py
```

| Script | Writes |
|---|---|
| `filter_error_code_report.py` | `output/A_B_position_report_<code>.csv` (A/B = first/last date, ISO) or `--out` |
| `correlate_cdn_ips.py` | `output/YYYY-MM-DD_cdn_correlation.csv`, `output/YYYY-MM-DD_mtn_escalation_ips.csv` |
| `build_mtn_summary.py` | `output/mtn_escalation_all_dates_rollup.csv`, `output/mtn_escalation_by_ip_summary_rollup.csv` |

## 6. Individual pipeline steps (run by hand)

```bash
python3 combine_lightstep_parts.py [--date 2026-10-06] [--input-dir D] [--remove-parts] [--dry-run]   # date is ISO here
python3 merge_ctap_smvod_csv.py --date 06102026 [--input-dir D] [--out O]
python3 run_athena_playback_outcome.py --date 2026-10-06 [--profile P] [--dry-run] [--skip-auth-check]  # ISO date
python3 run_athena_debug_events.py --date 2026-10-06 [--input F] [--profile P] [--dry-run] [--skip-auth-check]
python3 merge_session_outcome.py --date 06102026 [--input-dir D] [--report R] [--out O]
python3 lightstep_ctap_smvod_join.py --date 06102026 --org Synamedia-EU --project <project-id>   # live-API alternative to Step 2
```

## 7. Error eventdata analysis (`flatten_error_eventdata.py`, `summarize_error_eventdata.py`)

Part of `run_pipeline.py` (Steps 6f/6g; skip with `--skip-error-eventdata`) and also runnable by hand. They turn the raw `PLAYER_ERROR` debug-event `eventdata` JSON into analysis-ready columns.

**Flow (ZM, 4 Oct example).**

1. `python3 run_pipeline.py --date 04102026 --tenant ZM` runs everything below as Steps 6f and 6g, after the reports. Step 4 (`run_athena_debug_events.py`) is a different export: its
   `debug_states.csv` only has extracted columns (`sessionId, eventid, state, position, errorcode, errordescription, datetime`), with no `eventdata`, `messageid` or `clientid`.
2. Step 6f, `run_athena_error_eventdata.py --date 2026-10-04 --tenant ZM [--codes 3016,6007]`, exports every `PLAYER_ERROR` of the day to `data/athena/ZM/2026-10-04_error_eventdata.csv` (columns
   `datetime, messageid, clibversion, clientid, eventclass, eventid, eventdata`). It covers all tenant traffic for the day, not just Lightstep-matched sessions, so counts can exceed the pipeline error
   report. `--dry-run` prints the query; `--force` re-runs Athena over an existing CSV. The query is catalog slug `ctap-smvod-error-eventdata`.
3. Step 6g, `flatten_error_eventdata.py --split-by-errorcode`, writes `output/ZM/error_eventdata_flat/2026-10-04_all.csv` plus one `2026-10-04_<errorcode>.csv` per code.
4. Analyse with `summarize_error_eventdata.py` (see Run).
5. To find which sessions have errors first: `analyze_error_report_breakdown.py --all-codes --error-report ../output/ZM/2026-10-04_setupsession_with_outcome.csv`.

**Run by hand** (after step 2 or an Athena MCP export of the same columns):

```bash
cd investigations/ctap-smvod/scripts
python3 run_athena_error_eventdata.py --date 2026-10-04 --tenant ZM
python3 flatten_error_eventdata.py --input ../data/athena/ZM/2026-10-04_error_eventdata.csv \
    --date 2026-10-04 --out-dir ../output/ZM/error_eventdata_flat --split-by-errorcode
python3 summarize_error_eventdata.py --flat ../output/ZM/error_eventdata_flat/2026-10-04_all.csv --by errorcode,shaka_error_name
python3 summarize_error_eventdata.py --flat ../output/ZM/error_eventdata_flat/2026-10-04_3016.csv --by pipeline_status,net_effectivetype
```

**Output.** `<out>.csv` has one row per unique `messageid` (duplicates dropped, sorted by `datetime`) with every column plus the untouched `raw_eventdata`. `--split-by-errorcode` also writes `<out
stem>_<errorcode>.csv` per code, keeping only columns that have a value for that code. A row with invalid eventdata JSON aborts the run.

**Columns.** Each file has a common block for every code, plus a block that depends on the code.

| Group | Columns |
|---|---|
| Common | `datetime, messageid, deviceId, householdId, sessionId, errorcode, error_text, position, user_agent, is_wv, app_version` |
| Shaka error | `shaka_code, shaka_category, shaka_severity, shaka_handled, shaka_error_name, shaka_message` (first line only) |
| Shaka URL | `shaka_url, shaka_url_host, shaka_http_status, shaka_version` |
| 3xxx media (3016) | `media_error_type, pipeline_status` |
| 6007 DRM licence | `nested_error_name, nested_shaka_code, nested_http_status, nested_problem_type, nested_title, nested_detail` |
| 6007 MDRM | `nested_mdrm_http_status, nested_mdrm_code, nested_mdrm_message, flow_context` |
| Player state | `player_phase, player_readystate, player_isbuffering, player_ispaused, player_isseeking, player_networkstate` |
| Network | `net_type, net_effectivetype, net_downlink, net_rtt, net_savedata, drm_present` |
| Bandwidth and timing | `est_bandwidth_bps, est_bandwidth_mbps, stream_bandwidth_bps, stream_mbps, bytes_downloaded, load_latency_s, buffering_time_s` |
| Last ABR switch | `lastswitch_timestamp, lastswitch_id, lastswitch_type, lastswitch_bandwidth` |

`summarize_error_eventdata.py --by` takes comma-separated column names and can be repeated for several crosstabs. It only prints to stdout.

## 8. Ad-hoc helpers (explicit `--input`/`--out`, no date convention)

`extract_session_ids.py`, `extract_session_timeline.py`, `flatten_debug_events.py`, `build_debug_completeness_query.py`, `parse_debug_user_agents.py`, `analyze_debug_sample.py`,
`analyze_errorcode_correlation.py`, `analyze_api_timing.py` (subcommands), `analyze_session_guard_net_latency.py` (subcommands), `process_traces.py`. Run any with `--help` for its arguments.
