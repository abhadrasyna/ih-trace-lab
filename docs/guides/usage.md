# Running the `aws_access_cli` daily reports

`src/pipelines/aws_access_cli/scripts/run_daily_reports.py` is a thin orchestrator: one invocation takes a single `--date` and fans out across every configured tenant and all six sub-reports
(adoption, adoption-session, shaka-hhid, shaka-session, guest-session, shaka-1xxx-position). It has no built-in date-range/backfill option, so a multi-day run means invoking it once per day.

Run it as a module from the repo root (so `src.*` imports resolve) with the project's venv active:

```sh
python -m src.pipelines.aws_access_cli.scripts.run_daily_reports --date 2026-10-05
```

## Backfilling a range of dates

Loop over each date and redirect each run's stdout/stderr to its own dated log file under `logs/backfill/`, so a failed day is easy to isolate instead of being interleaved in one combined stream:

```sh
mkdir -p logs/backfill
start=2026-10-01
end=$(date +%Y-%m-%d)
d="$start"
while [ "$d" != "$(date -j -v+1d -f %Y-%m-%d "$end" +%Y-%m-%d)" ]; do
    python -m src.pipelines.aws_access_cli.scripts.run_daily_reports --date "$d" \
        >> "logs/backfill/run_daily_reports_${d}.log" 2>&1
    d=$(date -j -v+1d -f %Y-%m-%d "$d" +%Y-%m-%d)
done
```

`date -j -v+1d -f %Y-%m-%d` is the BSD/macOS `date` syntax this repo's dev machines use; swap in GNU `date -d "$d +1 day" +%Y-%m-%d` on Linux.

Each day's `>> logs/backfill/run_daily_reports_<date>.log 2>&1` redirect is independent of the application's own structured logging: `init_logging()` (called inside `main()`) always appends to the
single shared `logs/app.log` (path resolved from `config/data_paths.yaml`'s `logs_root`) regardless of how the process's stdout/stderr are redirected — see `src/lib/logging/setup.py`. The per-date
redirect above only captures anything printed straight to the console (tracebacks, `--preview` table output), which `app.log` does not separate by run.

## Live cron reference (legacy, pre-port)

See `docs/plan/pipeline-migration/aws-access-cli-pipeline-migration/audit.md`'s "Live crontab entries" section for the original `aws-access-cli` repo's single-date cron invocation this guide's
examples were adapted from; that section is a historical record of the pre-port script and intentionally left unchanged.
