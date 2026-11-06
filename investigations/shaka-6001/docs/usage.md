# shaka-6001 usage

How to run the Shaka 6001 ZA upgrade analysis, by hand or from cron. Every command runs from the repository root. Dates are ISO (`YYYY-MM-DD`); defaults (tenant `ZA`, start date, app versions, upgrade
window, `max_scan_gb`, `daily_lookback_days`) come from `investigations/shaka-6001/config/analysis.yaml`. Table timestamps are UTC; day and period logic is in IST.

## 1. Local data first

Every script reads local files first and only the two Athena steps ever query, and only for dates found in no local source:

1. `investigations/shaka-6001/data/athena/ZA/` (this investigation's own fetches),
2. `investigations/ctap-smvod/data/athena/ZA/`,
3. `investigations/ctap-smvod/output/ZA/`,
4. `output/ZA/` at the repository root.

A zero-byte file counts as absent. Fetched files are saved to source 1 and never refetched, so reruns and cron are idempotent. Outputs go to `investigations/shaka-6001/output/ZA/` (charts in
`.../charts/`); rerunning a range overwrites that range's outputs. `GUEST.*` ids are per-install, not real households or devices, and are kept in their own tables.

## 2. Scripts

All take `--start-date` (default: config start date), `--end-date` and `--tenant`; none needs a time of day. "Range files" are named `<start>_<end>_<artifact>.csv`.

| Step | Inputs | Outputs | Needs first |
|---|---|---|---|
| `build_enriched_events.py` | daily `*_error_eventdata_codes-6001.csv` (local only, never fetched) | `shaka6001_enriched` | none |
| `analyze_before_after.py` | enriched | `6001_before_after_webview`, `6001_before_after_model` | enriched |
| `analyze_versions_devices.py` | enriched, daily `session` files (optional) | `6001_by_chrome`, `_by_android`, `_mixed_webview_devices`, `_drm_*`, `_fail_then_success_devices` | enriched |
| `chart_before_after.py` | the before/after and by-chrome tables, enriched | PNGs in `charts/` | before/after tables |
| `fetch_guest_login_redirects.py` (Athena) | none (registered queries) | daily `guest_login_redirect` and `guest_redirect_debug_events` in the data folder | none |
| `analyze_guest_login_redirects.py` | the two daily guest files | `guest_redirect_daily`, `_periods`, `_steps`, `_preceding` | fetch (ordering only) |
| `build_6001_cohort.py` (Athena) | enriched, daily `session` files (fetched when missing) | `6001_cohort` | enriched |
| `analyze_6001_recovery.py` | cohort, enriched, daily `session` files | `6001_recovery_members`, `6001_recovery_summary`, PNGs | cohort |
| `rank_daily_top_impacted.py` | enriched, recovery members (optional) | top-N households and devices per day, guest and unassigned tables, PNGs | enriched |
| `rank_daily_top_models.py` | enriched | top-N device models per day, PNGs | enriched |
| `analyze_user_tenure.py` | daily `session` files (from 2026-10-01), cohort (optional) | `user_tenure_households`, `_buckets`, `_stickiness`, `_6001`, `_row_counts`, PNGs | cohort (ordering only) |

Ad hoc helpers outside the runner: `har_identity_timeline.py` (HAR identity timeline) and `propose_guest_pairs.py` (guest-to-real candidate pairs from Lightstep; read-only). Each script's `--help` has
the exact options.

Known limits: user tenure is measured from the earliest local session date, so households first seen on that date are left-censored (true tenure is longer) and the long buckets can be empty;
`drmsupported` is empty in events from before the upgrade, so DRM cuts only describe the after period.

## 3. Runner: `run_analysis.py`

```
python investigations/shaka-6001/scripts/run_analysis.py --end-date 2026-11-05
python investigations/shaka-6001/scripts/run_analysis.py --end-date 2026-11-05 --fetch-missing
python investigations/shaka-6001/scripts/run_analysis.py --end-date 2026-11-05 --only analyze_before_after,chart_before_after
python investigations/shaka-6001/scripts/run_analysis.py --end-date 2026-11-05 --dry-run
python investigations/shaka-6001/scripts/run_analysis.py --list
```

Steps live in a registry dict in `run_analysis.py` (`register(Step(...))`: script, dependencies, the daily files it fetches, its outputs); a new analysis registers itself and the runner never gets a
branch for it. Steps run in dependency order. `--end-date` defaults to the last complete UTC day (the only place the runner uses "today"); `--only` runs just the named steps and assumes their inputs
already exist.

Missing local dates of the fetchable inputs (sessions, guest redirect files) are reported up front, and the run stops before any query unless `--fetch-missing` is given. Missing 6001 error-event dates
are only warned about (the runner cannot fetch them). With `--fetch-missing`, AWS SSO is verified once through `src.lib.auth` before the first Athena step; a fetch estimated above `--max-scan-gb`
(default from config) is skipped with the reason logged. A failed or skipped step is `NOT RUN` for the steps that need its output, independent steps continue, the run ends with an OK / FAILED / NOT
RUN summary and the exit code is non-zero if anything is not OK (0 ok, 1 a step failed or was not run, 2 bad request or stopped for missing dates).

## 4. Daily mode: `run_daily.py`

```
python investigations/shaka-6001/scripts/run_daily.py
```

No arguments needed. It targets the last complete UTC day D and the IST day D it overlaps (IST day D is UTC D-1 18:30 to UTC D 18:30), rebuilds any of the previous `--lookback-days` (default from
config,
3) whose outputs are missing, then runs the full registry with `--fetch-missing` for the window config start date to D. One run at a time (lock `logs/run-daily.lock`; a second start logs and exits 0).
   Log: `investigations/shaka-6001/logs/run-daily_<D>.log`, 30-day prune, ending with the summary block. Any FAILED or NOT RUN step writes `output/ZA/<D>.FAILED.txt` and exits 1; a later clean run
   removes the note. If SSO cannot be verified non-interactively the Athena steps are NOT RUN, the local-data steps still run and the exit code is 1.

Crontab, 13:00 IST daily (the UTC day has ended). Cron has a minimal `PATH`, so set one that includes `aws`:

```
PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
0 13 * * * cd /Users/abhadra/myWork/myOffice/ih-trace-lab && .venv/bin/python investigations/shaka-6001/scripts/run_daily.py >> investigations/shaka-6001/logs/cron.out 2>&1
```

The machine must be awake at 13:00 and cron does not catch up missed runs (the lookback backfill covers a short gap). Installing the crontab is a human step; nothing here edits it.
