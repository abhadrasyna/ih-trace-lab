# CTAP/SM-VOD script usage

All commands run from `investigations/ctap-smvod/scripts/`. Dates are `DDMMYYYY` unless noted. Inputs and outputs are namespaced per tenant: outputs go to `../output/<TENANT>/` (per-date files are
prefixed `YYYY-MM-DD_`), Lightstep exports are read from `../data/lightstep/<TENANT>/`, Athena pulls go to `../data/athena/<TENANT>/`. Tenant codes come from `config/tenants.yaml` (`ZA`, `NG`, `ZM`,
`GH`); paths below that omit `<TENANT>/` for brevity are always under the tenant folder.

## 0. Multi-tenant model

```bash
python3 run_pipeline.py --date 06102026                # every tenant that has Lightstep input for the date
python3 run_pipeline.py --date 06102026 --tenant ZM    # one tenant only
python3 summarize_pipeline_run.py --date 06102026 --tenant ZM   # reconcile export row counts vs the merged report
python3 summarize_tenant_status.py --date 06102026              # ZA,GH,ZM status table (UTC day) -> docs/2026-10-06-tenant-status-summary.md (--tenants, --out, --force)
```

- With no `--tenant`, tenants with no `data/lightstep/<TENANT>/` input for the date are skipped. Within a tenant the pipeline stops at the first failing step; other tenants still run, a per-tenant
  summary prints, and the exit code is non-zero if any tenant failed.
- An unknown tenant, or a missing input folder, fails with a message naming the expected path.
- Standalone scripts (Steps 6b/6e/6d, ranges, rollups) take `--output-dir` / `--input-dir`; pass `../output/<TENANT>` explicitly, e.g. `python3 extract_error_report_1xxx_6xxx.py --from 01102026 --to
  06102026 --output-dir ../output/ZA`.

### Per-tenant Lightstep export rule

Export the ctap, smvod and smvod-ts files for the date into `data/lightstep/<TENANT>/`. For a tenant on a **shared** Lightstep project (`shared_project: true` in `config/tenants.yaml`, currently ZM
and GH on `mcs-go-prod-mtn-1-eu`), the Lightstep query must filter on the tenant's `busUnitId` (its `go_id`) and group by it, so the merge can verify no other tenant's rows are present:

| Export | Filter / group-by attribute |
|---|---|
| ctap | `sessionInfo.busUnitId` |
| smvod (sm-vod service) | `busUnitId` (no `sessionInfo.` prefix) |

Step 2 (`merge_ctap_smvod_csv.py`) fails loudly if any row is blank, mismatched, or the column is missing. Dedicated-project tenants (ZA, NG) need no `busUnitId` filter.

### Adding a tenant

1. Add the opco to `config/tenants.yaml` (resolve identifiers via `scripts/resolve_tenant.py`; see `docs/guides/tenant-resolution.md`).
2. Create `data/lightstep/<TENANT>/` and drop the exports in (with the `busUnitId` filter above if the project is shared).
3. Run `run_pipeline.py --date <d> --tenant <TENANT>` (Athena steps use the registry's tenant id, profile and region), then `summarize_pipeline_run.py` to reconcile counts.

## 1. Full pipeline (one date)

```bash
python3 run_pipeline.py --date 06102026
```

Prerequisite: the Lightstep exports for the date already sit in `data/lightstep/<TENANT>/` (`YYYY-MM-DD_ctap.csv`, `YYYY-MM-DD_smvod.csv`, `YYYY-MM-DD_smvod-ts.csv`, or numbered `_NN_` parts of each).
Step 1 is manual.

Step 0 (`check_lightstep_inputs.py`, runs first for every tenant, bypass with `--skip-input-check`) fails the whole run before any step starts when: a required file is absent; numbered parts have a
gap or differ between `ctap`/`smvod`/`smvod-ts`; a combined file was built from a deleted part; a file lacks required columns or rows; rows belong to another tenant; or `smvod-ts` (the only export
with timestamps) starts or ends more than 15 minutes from 00:00/24:00 UTC or leaves a gap over 15 minutes between parts. A last part at the 500-row cap, and mDRM part-numbering gaps, only warn. Run it
alone with `python3 check_lightstep_inputs.py --date DDMMYYYY [--tenant T] [--drm]`; new artifacts are added in the registries at the top of `scripts/lib/lightstep_inputs.py`.

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
| 6h | `run_3016_subcategory_report.py` | `output/<T>/subcategory_3016/<date>_subcategory_{summary,events}.csv` (§7d) |

Variations:

```bash
python3 run_pipeline.py --date 06102026 --dry-run                    # print commands only, touch nothing
python3 run_pipeline.py --date 06102026 --skip-step3 --skip-step4    # reuse existing Athena CSVs
python3 run_pipeline.py --date 06102026 --skip-if-exists             # skip Athena per step only if its CSV exists
python3 run_pipeline.py --date 30102026 --skip-step3 --skip-input-check --table-suffix oct26 --force   # past-month debug re-pull (Steps 4/6f)
python3 run_pipeline.py --date 06102026 --skip-step6b                # no position_report.csv
python3 run_pipeline.py --date 06102026 --skip-step6e                # no 1xxx/6xxx error report
python3 run_pipeline.py --date 06102026 --skip-step6d                # no webview device report
python3 run_pipeline.py --date 06102026 --skip-error-eventdata       # no raw error eventdata export + flatten (Steps 6f/6g)
python3 run_pipeline.py --date 06102026 --skip-subcategory-3016       # no 3016 sub-category report (Step 6h; also skipped by --skip-error-eventdata, which supplies its input)
python3 run_pipeline.py --date 06102026 --drm                         # Step 6h adds mDRM device columns + summary (needs data/lightstep/<TENANT>/ exports, see lightstep-drm-exports.md)
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
python3 extract_error_report_1xxx.py --from 01102026 --to 06102026                 # 1xxx only, ZA,GH,ZM at once: one XLSX per tenant in output/<TENANT>/ (--tenants, --output-dir ROOT)
python3 combine_error_report_1xxx_csv.py --tenant ZA --from 01102026 --to 11102026 # 1xxx, ONE tenant, ONE CSV (leading `date` column): output/ZA/<range>_error_report_1xxx_combined.csv
python3 rank_households_by_error.py --xlsx ../output/ZA/2026-10-01_2026-10-13_error_report_1xxx.xlsx --top 25  # households by error sessions
```

| Mode | Output |
|---|---|
| `--date D` | `output/YYYY-MM-DD_error_report_1xxx_6xxx.csv` |
| `--from A --to B` | `output/A_B_error_report_1xxx_6xxx.xlsx` (ISO dates; sheets named `YYYY-MM-DD`) |

Other options: `--output-dir`. `rank_households_by_error.py` takes `--xlsx` or a single-day `--csv` (e.g. `--csv ../output/ZA/2026-10-20_error_report_1xxx.csv --top 10`), and also reports days,
devices (count plus `;`-separated `deviceIds`) and error codes per household and writes the full ranking to `<input stem>_household_ranking.csv` (`--out-dir`).

### Combine per-error-code files across opcos (`combine_error_code_by_opco.py`)

Merges the `output/<TENANT>/error_eventdata_flat/<date>_<errorcode>.csv` files (the `_all.csv` files are ignored) into **one XLSX per error code** (flattened columns differ by code, so codes are never
mixed): one sheet per opco, all dates stacked, with a leading `date` column and a trailing `content_title` column (joined by `sessionId` from `output/<TENANT>/*_setupsession_with_outcome.csv`,
`(unmatched)` if not found). An opco with no rows for a code gets no sheet. Tenants are auto-discovered; the date range and `--codes` are optional (omit them for every date and code found). Reads
existing files only.

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
| `python3 analyze_error_report_breakdown.py --error-report ../output/ZA/2026-10-09_error_report_1xxx_6xxx.csv [--outcome-report ...]` | stdout only (error code / `is_wv` / device / hour breakdown) |
| `python3 analyze_error_report_breakdown.py --all-codes --error-report ../output/ZM/2026-10-04_setupsession_with_outcome.csv` | same breakdown over every error code (incl. 3016) |
| `python3 flatten_error_eventdata.py --input <export>.csv --date <date> --out-dir ../output/ZM/error_eventdata_flat` | `<date>_all.csv`: `eventdata` split into columns + `raw_eventdata` |
| `python3 flatten_error_eventdata.py ... --split-by-errorcode` | also `<date>_<errorcode>.csv` per code, columns blank for that code dropped |
| `python3 summarize_error_eventdata.py --flat <flat>.csv --by errorcode,net_effectivetype` | stdout only (counts/crosstab over flat columns; `--by` repeatable) |
| `python3 count_error_by_content.py --from 2026-10-01 --to 2026-10-10 --tenants ZA` | `output/<TENANT>/<from>_<to>_error_6xxx_by_content[_rollup].csv` (`sessions,unique_households`) |
| `python3 compute_concurrent_playback.py --date 2026-10-14 --tenants ZA,GH,ZM` | `output/<TENANT>/<date>_concurrent_playback[_summary].csv` (per UTC minute, three views); see note below |
| `python3 chart_concurrent_playback.py --date 2026-10-14 --tenants ZA,GH,ZM` | `output/<TENANT>/charts/<date>_concurrent_playback.png` (run compute first; a chart failure is logged, CSVs stay) |
| `python3 chart_playback_attempts.py --date 2026-10-14 --tenants ZA,GH,ZM [--bucket-min 5]` | `output/<TENANT>/charts/<date>_playback_attempts.png` (unique-session attempts per bucket) |
<!-- lint-ignore-length -->
| `python3 run_athena_session_ingest.py --date 2026-10-14 --tenant ZA` | `data/athena/<TENANT>/<date>_session_ingest.csv` (`sessionId,event_start,ingest_timestamp`, partitions D-1 and D; catalog `ctap-smvod-session-ingest`) |
<!-- lint-ignore-length -->
| `python3 chart_playback_attempts.py --date 2026-10-14 --tenants ZA --time-field ingest` | `output/<TENANT>/charts/<date>_playback_attempts_ingest.png` (attempts at each session's earliest `ingest_timestamp`; run the export first; sessions that started that day but landed on another are counted in the title) |
<!-- lint-ignore-length -->
| `python3 compare_lightstep_athena_sessions.py --date 2026-10-14 --tenant ZA` | stdout counts (both / Lightstep-only / Athena-only) + `output/<TENANT>/<date>_lightstep_vs_athena_sessions.csv` (one row per one-sided session; Lightstep side = `setupsession.csv`, Athena side = `data/athena/<T>/<date>_session.csv`, enriched from `_session_ingest.csv` when present) |
<!-- lint-ignore-length -->
| `python3 run_athena_debug_sessions.py --date 2026-10-14 --tenant ZA [--table-suffix sept26]` | `data/athena/<TENANT>/<date>_debug_sessions.csv` (`sessionId,first_event`: distinct `abr-vod-` sessions with a PLAYER_SESSION_EVENT/STATE_CHANGE/ERROR in the UTC day; catalog `ctap-smvod-debug-sessions`) |
<!-- lint-ignore-length -->
| `python3 compare_lightstep_athena_sessions.py --date 2026-10-14 --tenant ZA --debug` | as above plus the debug-events set: per-region counts (L/U/D Venn) on stdout and an `in_debug` column in the mismatch CSV |
<!-- lint-ignore-length -->
| `python3 export_lightstep_day.py --tenant ZA --date 2026-10-30 --kinds smvod-release` (also for D+1) | `data/lightstep/<TENANT>/<date>_smvod-release.csv` (`sessionId,http.status_code,externalTeardownReason`: every sm-vod `Release` span; query `queries/lightstep/lightstep-export-smvod-release.md`; also part of the default export). Lightstep keeps about 7 days |
<!-- lint-ignore-length -->
| `python3 analyze_ebvs_release_coverage.py --date 2026-10-30 --tenant ZA` | stdout table per Athena `playback_outcome` (sessions, with SetupSession, with Release, SetupSession-without-Release, `release_missing_pct` over sessions with a SetupSession) + `output/<TENANT>/<date>_ebvs_release_coverage.csv` (one row per Athena session with `has_setup`/`has_release`). Needs `<date>_session.csv`, `<date>_smvod.csv` and `<date>_smvod-release.csv`; reads D+1's release file when present. The non-EBVS outcomes are the control for a general Release gap |
<!-- lint-ignore-length -->
| `python3 analyze_release_gap_webview.py --date 2026-10-30 --tenant ZA` | stdout table per `playback_outcome` of sessions with a SetupSession but no Release, split WebView / non-WebView / unknown (`wv_pct_of_known`) + `output/<TENANT>/<date>_release_gap_webview.csv` (`sessionId`, `playback_outcome`, `is_wv`). Needs `<date>_ebvs_release_coverage.csv` (run `analyze_ebvs_release_coverage.py` first) and `<date>_setupsession_with_outcome.csv`. ZA 2026-10-30: 62.9% WebView overall (EBVS 87.0%, DESTROY 1.7%), so the Release gap is not WebView-only |
<!-- lint-ignore-length -->
| `python3 build_session_comparison_daily.py --from 2026-10-14 --to 2026-10-14 [--tenants ZA,GH,ZM]` | `output/<OPCO>/daily/<YYYY-MM>_session-comparison.csv` (adoption-report style: per-opco month file, one row per `session_date`): unique-session counts for Lightstep / unified / debug, their pairwise and triple overlaps and `*_not_*` differences. Local inputs only; a missing input leaves its columns blank (named in `missing_inputs`), a tenant/day with no inputs is skipped, reruns replace the same day (locked atomic upsert). Default tenants: all in `config/tenants.yaml` |
| `python3 find_codec_support_content.py --from 2026-10-01 --to 2026-10-11 --tenant ZA --codec ec-3` | `output/<TENANT>/<from>_<to>_ec-3_true_by_content[_sessions\|_split].csv` |
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

## 7b. Error eventdata for sessions in a report (`extract_household_error_eventdata.py`)

Pulls every local `data/athena/<TENANT>/*_error_eventdata.csv` row whose `eventdata` JSON `sessionid` is in an error-report CSV (e.g. the 3xxx household report), adding
householdId/deviceId/sessionId/source_file, sorted by session and datetime. Never calls Athena; logs sessions with no local rows.

```bash
python3 extract_household_error_eventdata.py --report-csv ../output/ZA/2026-10-01_2026-10-19_error_report_3xxx_rD_saW-t.csv --tenant ZA   # -> <report>_error_eventdata.csv (--out, --data-dir)
```

## 7c. All debug events for a household/device (`run_athena_household_debug_events.py`)

Live Athena query (catalog slug `ctap-smvod-household-debug-events`) for EVERY event (all eventclass/eventid, full eventdata) of the householdId/deviceId pairs in an error-report CSV, matched on
`clientid = '<deviceId>:<householdId>'` over an inclusive date range. Needed because local `debug_states`/`error_eventdata` hold only a filtered subset.

```bash
python3 run_athena_household_debug_events.py --report-csv ../output/ZA/2026-10-01_2026-10-19_error_report_3xxx_rD_saW-t.csv --tenant ZA --from 2026-10-01 --to 2026-10-21
# -> <report>_debug_events_all.csv (--dry-run, --out, --force)
# --table-suffix oct26 queries the month table <id>_ccl_debug_events_oct26 (output gets a _oct26 suffix: <report>_debug_events_all_oct26.csv)
```

## 7c2. One household's sessions with DRM info (`trace_household_sessions.py`)

Given a householdId, builds a table of `sm-vod` sessionIds joined to `go-mdrmfe` (DRM type, `brRef`, `fcid`), the US mDRM licence chain and CDM device (make/model/security level) by `fcid`, and an
`outcome` whose prefix names the system that gave the evidence, also written to the `evidence_layer` column (`ATHENA`, `SMVOD`, `MDRMFE`, `MDRM`). Lightstep-only outcomes: `SMVOD_CREATE_NON_2XX`
(`sm-vod` POST not 2xx), `MDRMFE_SPAN_NOT_SEEN` (no `go-mdrmfe` span, may be sampled away), `MDRMFE_STATUS_NON_2XX` (`go-mdrmfe` span not 2xx), `MDRM_US_HOP_NON_2XX` (a US licence hop not 2xx),
`MDRM_LICENSE_OK_NO_ATHENA` (all 2xx, playback unconfirmed).

With `--athena` it also queries `unified_sessions` by household (`user_id`, one cheap query, catalog `ctap-smvod-household-unified-sessions`) and adds `content_title`, `unified_content_id`,
`unified_endreason` and `play_seconds` (PLAY row). Athena outcomes win over the Lightstep ones: `ATHENA_SESSION_PLAYER_ERROR`, `ATHENA_SESSION_PLAYED`, `ATHENA_SESSION_OTHER_ENDREASON`. Only for
`PLAYER_ERROR` sessions it then pulls their debug events (about 2 GB scanned per month table) into `debug_error_code`, `debug_error_text`, `debug_shaka_error` and `debug_user_agent`. The table is
found with `SHOW TABLES` by session month (the unsuffixed table is the current month; `--table-suffix oct26` overrides). If that lookup fails the CSV is still written and the script exits 1. Lightstep
keeps about 7 days; for older windows `--athena` still lists the sessions. The hhid is validated and bad input fails loudly. Tokens: `LIGHTSTEP_API_KEY_EU` / `LIGHTSTEP_API_KEY_US` (env or root
`.env`). Pure logic: `scripts/lib/household_trace.py`.

```bash
python3 trace_household_sessions.py --tenant ZA --hhid <householdId> --from 2026-11-03T12:00:00 --to 2026-11-03T15:00:00
python3 trace_household_sessions.py --tenant ZA --hhid <householdId> --from 2026-11-03 --to 2026-11-03 --athena
# -> output/<TENANT>/<hhid8>_<hhid-last8>_session_trace.csv (+ _unified_sessions.csv, _debug_tables.csv, _debug_events[_<suffix>].csv with --athena)
```

## 7d. Daily 3016 sub-category report (`run_3016_subcategory_report.py`)

Splits the SMVOD player errors 3014/3015/3016 into the 5 "Media Playback Errors" triage sub-categories. Reads local files only (no Athena/Lightstep), per OpCo and day, from `output/<OPCO>/`:
`error_eventdata_flat/<date>_all.csv` (required; missing file exits with an error), plus `<date>_setupsession_with_outcome.csv` and `<date>_position_report.csv` (optional; if missing a warning is
printed and the `join_*` columns stay false). Joined by `sessionId` (first row per session; empty ids never join).

```bash
python3 run_3016_subcategory_report.py --opco ZA --date 2026-10-22          # or --from 2026-10-20 --to 2026-10-22; --base, --out
# -> output/ZA/subcategory_3016/<date>_subcategory_summary.csv  (date,opco,subcategory,events,households,sessions,priority)
# -> output/ZA/subcategory_3016/<date>_subcategory_events.csv   (one row per error, incl. raw user_agent, parsed browser/device_model, content_uuid, hh_repeat_events, content_distinct_hh)
```

The events row count must equal the day's 3014/3015/3016 rows in the flat file, otherwise the run raises. Rules (`classify_3016_subcategory.py`, first match wins):

| Order | Condition | Sub-category | Priority |
|---|---|---|---|
| 1 | `errorcode` 3014 or 3015 | MSE append failed (3014/3015) | P3 |
| 2 | `pipeline_status` contains "reinitialization failed" | Video decoder re-initialisation failed | P2 |
| 3 | `media_error_type` is 4 and `pipeline_status` empty | No data / source not supported | P2 |
| 4 | `pipeline_status` contains "audio" or "disconnected" | Audio decode / pipeline disconnected | P3 |
| 5 | `pipeline_status` contains "decode" | Video decode error | P1 |
| 6 | anything else | Uncategorised | P? |

No automatic pattern verdict is produced; analyse the events CSV. Segment URLs exist only on 3014/3015 events.

### 3016 DRM device link (`--drm`)

`--drm` links each event to the mDRM license request and CDM row. It reads the five hand-saved exports (mdrmfe, Widevine, PlayReady, FairPlay, LRM; see `docs/lightstep-drm-exports.md`) from
`data/lightstep/<OPCO>/` (or `--drm-dir`), joins `sessionId` to `fcid` to the CDM row (`scripts/build_3016_drm_link.py`, readers in `scripts/lib/drm_exports.py`), and appends `fcid, drm_type, br_ref,
cdm_make, cdm_model, platform, security_level, license_status, drm_join` to the events CSV (row count unchanged, otherwise the run raises). `scripts/build_3016_drm_device_summary.py` also writes
`<date>_subcategory_device_summary.csv` (events, households and `license_ok` per sub-category and CDM model).

```bash
python3 run_3016_subcategory_report.py --opco ZA --date 2026-10-22 --drm
```

`drm_join` is one of `joined`, `no_license_request` or `no_cdm_row`; empty `sessionId`, `fcid` or `fcId` never join.

ZA 2026-10-22 (43 events): 39 `joined`, 4 `no_license_request` (the 3 "No data / source not supported" events and 1 "MSE append failed"), 0 `no_cdm_row`. All 39 joined events have license status 200,
so these errors are not license failures. Video decode error (32 events, 15 households), by device model:

| Device model | Events | Households |
|---|---|---|
| Samsung dream2lte (Widevine L1) | 10 | 5 |
| Samsung r8s (Widevine L1) | 9 | 2 |
| Samsung a13 (Widevine L1) | 5 | 3 |
| Samsung a5ulte (Widevine L1) | 3 | 1 |
| Apple iPhone (FairPlay) | 2 | 2 |
| Samsung a12s (Widevine L1) | 2 | 1 |
| Samsung a04e (Widevine L1) | 1 | 1 |

## 7e. mDRM funnel and reports (`analyze_drm_funnel.py`, `analyze_mdrm_quality.py`, `analyze_mdrm_devices.py`)

All three read the hand-saved mDRM exports (`docs/lightstep-drm-exports.md`) from `data/lightstep/<OPCO>/` (or `--drm-dir`) and write to `output/<OPCO>/drm-analysis/` (markdown reports at the top,
`csv/` for CSVs, `charts/` for PNGs; shared path helper `scripts/lib/drm_output.py`); no Athena or Lightstep calls.

```bash
python3 analyze_drm_funnel.py --opco ZA --date 2026-10-23     # <date>_drm_funnel.md + csv/<date>_drm_funnel.csv + charts/ (5 PNGs); Step 6i; --absolute = raw counts
python3 analyze_mdrm_quality.py --opco ZA --date 2026-10-23   # <date>_mdrm_quality.md + csv/<date>_mdrm_quality_failures.csv (statuses, failing fcIds, retries, fcId chain, part overlap)
python3 analyze_mdrm_devices.py --opco ZA --date 2026-10-23 [--min-volume 5]  # <date>_mdrm_devices.md + Widevine level/brRef chart
```

`run_pipeline.py` runs all three as Steps 6i-6k, together: one `--skip-drm-reports` flag (alias `--skip-drm-funnel`) skips them and `--drm-dir` applies to all; they are also skipped when the mdrmfe or
LRM export is missing for the date. The funnel needs `<date>_setupsession_with_outcome.csv` (Step 5) in `output/<OPCO>/`.

## 7f. Bandwidth vs playback failure (`run_athena_session_bandwidth.py`, `analyze_bandwidth_vs_failure.py`, `chart_bandwidth_vs_failure.py`)

Tests whether low bandwidth explains failures, per `sessionid`, from the tenant's debug events (catalog slug `ctap-smvod-session-bandwidth`). Shaka's `estimatedbandwidth` is only logged on
`PLAYER_ERROR`, so healthy sessions only have the ABR bitrate (`PLAYER_TRACK_CHANGE`); the stats and their plain-language meaning are in `docs/2026-10-29_ZA_bandwidth-vs-playback-failure.md`. Not part
of `run_pipeline.py`.

```bash
cd investigations/ctap-smvod/scripts
python3 run_athena_session_bandwidth.py --date 2026-10-24 --tenant ZA   # data/athena/ZA/<date>_session_bandwidth.csv, one row per session (--dry-run, --force)
python3 analyze_bandwidth_vs_failure.py --date 2026-10-24 --tenant ZA    # output/ZA/bandwidth/<date>_{bandwidth_by_errorcode,abr_failure_rate,bandwidth_stats,effectivetype_by_errorcode}.csv
python3 chart_bandwidth_vs_failure.py --date 2026-10-24 --tenant ZA      # output/ZA/charts/<date>_{bw_spread_by_errorcode,bw_coverage_by_errorcode,buffering_vs_healthy,...}.png (5 PNGs)
```

Statistics logic is in `scripts/lib/bandwidth_stats.py` (pure functions: percentiles, Spearman, Mann-Whitney, ABR-bucket failure rate); tests in `tests/test_bandwidth_vs_failure.py`.

## 7g. Daily cron pipeline (`run_daily_pipeline.py`)

One command runs the whole daily chain for a UTC day (default yesterday): `export_lightstep_day.py` per tenant, `check_lightstep_inputs.py --drm`, then per tenant `run_pipeline.py --tenant T --drm
--skip-input-check`, `extract_error_report_1xxx.py --tenants T` and `rank_households_by_error.py --top 10`. Options: `--date DDMMYYYY|YYYY-MM-DD`, `--tenants ZA,GH,ZM`, `--skip-export`, `--from-step
export|check|pipeline|report|rank|coverage` (resume at that step after a failure, e.g. `--from-step rank`), `--skip-input-check` (drops the advisory `check inputs` step), `--ebvs-release-coverage`
(opt-in last step: `analyze_ebvs_release_coverage.py` per tenant for the day `--coverage-lag-days` (default 1) before the run day; a tenant missing that day's `session`/`smvod`/`smvod-release` CSV is
skipped with a warning, never a failure; implied by `--from-step coverage`; each tenant's coverage step is followed by `analyze_release_gap_webview.py` for the same day, skipped with a warning when
that day's `setupsession_with_outcome.csv` is missing), `--workers 1-8` (passed to the export, default 4), `--table-suffix oct26` and `--force` (passed to `run_pipeline.py` only, to re-read a past
month's debug table; a warning is logged when the day is not in the current UTC month and no suffix is given), `--top`, `--log-dir`. A Lightstep kind that returns no series for a day (normal for a
small tenant) is not a failure: the exporter writes a header-only CSV, logs a `WARNING` (tenant, kind, day), and the summary shows the export as `OK with warning`; an empty result for a day older than
the 7-day retention window is still an error, as are auth, transport and malformed-response errors. A failed step blocks only the later steps of the same tenant (shown `NOT RUN`); other tenants
continue, a failed export whose 9 CSVs were all written (e.g. only the input check failed) and the advisory steps let the tenant continue too; the final exit is still non-zero on any failure or
missing output CSV. The input check reports a header-only mDRM file as WARN but a header-only `ctap`/`smvod`/`smvod-ts` as FAIL. One FCID covers the run and is passed to the steps as `FCID`. Log:
`logs/run-daily-pipeline_<date>.log` (30-day prune); cron stdout/stderr: `logs/cron.out`. The log ends with a `==== run summary ====` block: OK / FAILED / NOT RUN per step, SKIPPED coverage tenants
with the missing file, and a ready-to-paste `to resume: ... --from-step <group>` line (with `--tenants` narrowed to the tenants that still have steps to redo).

```
python3 scripts/run_daily_pipeline.py --date 29102026 --skip-export
```

Crontab, 13:00 IST daily (the UTC day has ended; Lightstep keeps about 7 days). Cron has a minimal `PATH`, so set one that includes `aws` and `aws-sso`:

```
PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
0 13 * * * cd /Users/abhadra/myWork/myOffice/ih-trace-lab && .venv/bin/python investigations/ctap-smvod/scripts/run_daily_pipeline.py >> investigations/ctap-smvod/logs/cron.out 2>&1
```

AWS SSO: `run_pipeline.py` Steps 3/4 pre-flight the SSO session and refresh it through `aws-sso`; if that cannot happen non-interactively the step fails fast and the wrapper exits non-zero. A Mac must
be awake at 13:00 (cron does not catch up missed runs).

## 8. Ad-hoc helpers (explicit `--input`/`--out`, no date convention)

`extract_session_ids.py`, `extract_session_timeline.py`, `flatten_debug_events.py`, `build_debug_completeness_query.py`, `parse_debug_user_agents.py`, `analyze_debug_sample.py`,
`analyze_errorcode_correlation.py`, `analyze_api_timing.py` (subcommands), `analyze_session_guard_net_latency.py` (subcommands), `process_traces.py`. Run any with `--help` for its arguments.
