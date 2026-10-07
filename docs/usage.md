# aws-access-cli usage

All commands run from the repo root as `python -m <module>`. Tenants: `ZA` (South Africa), `ZM` (Zambia), `GH` (Ghana), `NG` (Nigeria). Dates are `YYYY-MM-DD`; months are `YYYY-MM`. Module prefix used
below: `src.pipelines.aws_access_cli.scripts`.

## Scheduled orchestrators (all tenants, all sub-reports)

These loop over every tenant and run the listed sub-reports. Existing outputs are skipped unless `--force` is given. Auth is checked once up front.

| Script | Required arg | Sub-reports |
|---|---|---|
| `run_daily_reports` | `--date` | adoption, adoption-session, shaka-hhid, shaka-session, guest-session, shaka-1xxx-position |
| `run_weekly_reports` | `--week` (week start date) | adoption, adoption-session, shaka-hhid, shaka-session, guest-session |
| `run_monthly_reports` | `--month` | adoption, adoption-session, shaka-hhid, shaka-session, guest-session |

### Catch-up of missed periods (on by default)

Each run also processes the periods before the target, oldest first, so a missed run (e.g. laptop off) is filled by the next one. Periods whose output already has data are skipped before Athena is
queried.

| Option | Applies to | Default | Meaning |
|---|---|---|---|
| `--lookback-days N` | daily | 7 | Also process the N days before `--date` |
| `--lookback-weeks N` | weekly | 4 | Also process the N weeks before `--week` |
| `--lookback-months N` | monthly | 3 | Also process the N months before `--month` |
| `--no-catch-up` | all three | off | Process only the target period |
| `--force` | all three | off | Re-run Athena for the target period even if it has data; does not apply to the lookback periods |

```bash
# Normal scheduled run (yesterday + up to 7 days of gaps)
python -m src.pipelines.aws_access_cli.scripts.run_daily_reports --date 2026-10-07

# Only one day, no gap filling
python -m src.pipelines.aws_access_cli.scripts.run_daily_reports --date 2026-10-07 --no-catch-up

# Recreate one day (overwrites that day's rows)
python -m src.pipelines.aws_access_cli.scripts.run_daily_reports --date 2026-10-07 --force --no-catch-up

# Widen the gap window to 14 days
python -m src.pipelines.aws_access_cli.scripts.run_daily_reports --date 2026-10-07 --lookback-days 14

# Weekly and monthly
python -m src.pipelines.aws_access_cli.scripts.run_weekly_reports --week 2026-09-30
python -m src.pipelines.aws_access_cli.scripts.run_weekly_reports --week 2026-09-30 --force --no-catch-up
python -m src.pipelines.aws_access_cli.scripts.run_monthly_reports --month 2026-09
python -m src.pipelines.aws_access_cli.scripts.run_monthly_reports --month 2026-09 --lookback-months 6
```

A gap longer than the lookback is not recovered automatically; raise the lookback or run the date directly.

## Historical backfills (date ranges)

Both take `--start-date` and `--end-date` (required) and `--force`, and run all tenants. They pass the range to each sub-report, so they write range-named files (e.g.
`2026-10-01_2026-10-07_adoption-report.csv`), not the per-month files.

| Script | Extra args | Sub-reports |
|---|---|---|
| `run_historical_backfill` | none | The six daily sub-reports. Currently fails on `shaka-1xxx-position`, which supports a single `--date` only |
| `run_historical_period_reports` | `--period week\|month` (required) | The five weekly/monthly sub-reports |

```bash
python -m src.pipelines.aws_access_cli.scripts.run_historical_period_reports --start-date 2026-08-01 --end-date 2026-09-30 --period month
```

To refill individual days in the per-month files, use `run_daily_reports` with `--lookback-days` or one `--force --no-catch-up` run per date.

## Individual reports (one tenant)

Every report below accepts the shared options in the next section. Pass `--tenant` to pick one tenant.

| Script | Output artifact |
|---|---|
| `run_adoption_report` | `adoption-report` (household metrics) |
| `run_adoption_session_report` | `adoption-session-report` |
| `run_guest_session_report` | `guest-session-report` |
| `run_shaka_error_hhid_report` | `shaka-error-hhid` |
| `run_shaka_error_session_report` | `shaka-error-session` |
| `run_shaka_1xxx_position_report` | `shaka-1xxx-position-report` (single `--date` only) |
| `run_adoption_gap_analysis_report` | `adoption-gap-analysis` |
| `run_adoption_gap_analysis_session_report` | `adoption-gap-analysis-session` |
| `run_incomplete_no_destroy_investigation` | `incomplete-no-destroy-session-ids` |

```bash
python -m src.pipelines.aws_access_cli.scripts.run_adoption_report --date 2026-10-07 --tenant ZA
python -m src.pipelines.aws_access_cli.scripts.run_adoption_report --week 2026-09-30 --tenant ZA --period week
python -m src.pipelines.aws_access_cli.scripts.run_adoption_report --month 2026-09 --tenant ZA --period month
python -m src.pipelines.aws_access_cli.scripts.run_adoption_report --date 2026-10-07 --tenant ZA --force --preview
```

### Shared options

| Option | Meaning |
|---|---|
| `--date`, `--start-date`/`--end-date`, `--week`, `--month` | Period selection; one of these is required |
| `--period day\|week\|month` | Cadence for the output folder and file layout (default `day`) |
| `--tenant CODE` | `ZA`, `ZM`, `GH` or `NG` |
| `--force` | Re-run Athena even if the output CSV already has this period's data |
| `--dry-run` | Show what would run without querying or writing |
| `--preview` | Print a summary of the rows |
| `--skip-auth-check` | Skip the AWS session check (the orchestrators do this themselves) |
| `--output-dir`, `--log-dir`, `--profile`, `--workgroup`, `--output-location`, `--region`, `--poll-interval`, `--timeout`, `--table` | Runtime overrides; defaults come from the runtime config |

## Ad-hoc catalog query

```bash
python -m src.pipelines.aws_access_cli.scripts.run_athena_query <query_name> --tenant ZA --date 2026-10-07 --param KEY=VALUE
```

`--param` can be repeated and must be `KEY=VALUE`.

## One-time migration

```bash
python -m src.pipelines.aws_access_cli.scripts.seed_shaka_perpetual_headers [--legacy-root DIR] [--output-dir DIR] [--tenant CODE] [--dry-run]
```

Copies the legacy Shaka column order into the weekly/monthly perpetual files. It is idempotent and never touches a file this repo has already created.

## Cron

The schedule runs yesterday's daily report at 06:00, the weekly report on Mondays at 07:00 and the monthly report at 22:00 on the last day of the month. Because a run for a date that already has data
is skipped, running a report for a day that is still in progress leaves a partial row; fix it with `--force --no-catch-up` once the day is complete.

## Output files

Output goes under `output/<TENANT>/{daily,weekly,monthly}/`. Per-month files such as `2026-10_adoption-report.csv` hold one row per day. The `*.lock` files next to them are file-lock sidecars created
while a file is updated; they are safe to ignore and are gitignored.
