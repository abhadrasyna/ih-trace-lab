# Household usage tracking pipeline

A daily, read-only report of sm-vod/CTAP playback per tracked household and device, per tenant (ZA for now). It reads the ctap-smvod pipeline's local exports by default and writes
`output/reports/usage/<TENANT>/<YYYY-MM-DD>.md`. Story: `docs/plan/household-usage-tracking/`.

## Inputs

- `config/tracked_households.yaml` is the only file a user edits: each household has `tenant`, `hhid`, `label`, `track`, `phone` and `members` (`name`, `device_id`). `track: false` households are
  skipped. Any device seen on a tracked HHID but missing from `members` is flagged `new_device` in Anomalies.
- Local exports, produced by the ctap-smvod download pipeline (it runs for D-2 at 13:00): `investigations/ctap-smvod/data/athena/<TENANT>/<date>_session.csv`, `_debug_states.csv` and
  `investigations/ctap-smvod/data/lightstep/<TENANT>/<date>_smvod.csv`. The 7-day trend needs the session export of each of the 7 days ending on the report day. A missing file fails the run; it never
  becomes a zero.
- `--live-athena` / `--live-lightstep` query that source live instead (SSO login for Athena, `LIGHTSTEP_*_API_KEY` in the gitignored `.env`). Use them for a day the download pipeline has not covered
  yet.

## Run

```
python -m src.pipelines.usage_tracking.scripts.run_daily_usage_report --date 2026-11-02
```

`--date` defaults to two days ago. Other options: `--config`, `--out-dir` (default `output/reports/usage`), `--live-athena`, `--live-lightstep`. Running the same date again overwrites that report.

## Outputs and failure behaviour

- Success: `output/reports/usage/<TENANT>/<date>.md` (summary, per-household table, per-person session detail, Anomalies, 7-day trend) and exit code 0.
- Failure (roster, missing export, Athena or Lightstep error, SSO refresh): the run logs the error once, writes `output/reports/usage/<TENANT>/<date>.FAILED.txt` saying "report not generated" and why
  (a roster failure writes `output/reports/usage/<date>.FAILED.txt`), writes no partial report, and exits 1. A later successful run removes the stale note.
- Logs go through `init_logging("daily-usage-report")` (one FCID per run).

## Schedule

The user installs this line (same style as the other ih-trace-lab jobs, after the 13:00 download; the default D-2 offset is the newest day the download pipeline has produced):

```
0 14 * * * cd $REPO && $PY -m src.pipelines.usage_tracking.scripts.run_daily_usage_report --date "$(date -v-2d +\%Y-\%m-\%d)" >> $LOGS/cron_usage_report.out 2>&1
```

## Layout

`roster` ← `athena_source`, `lightstep_source` ← `merge` ← `rules` ← `render` ← `scripts/run_daily_usage_report` (`live_clients` builds the live sources only when a `--live-*` flag is set). Every
external system is injected through the `SessionSource` / `RequestSource` Protocols; exceptions derive from `UsageTrackingError`. Not covered: other event types, alerting or delivery, backfill.
