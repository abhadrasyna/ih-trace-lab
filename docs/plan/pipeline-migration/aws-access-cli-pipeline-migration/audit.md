# aws-access-cli `scripts/` audit

## Scope and classification rule

This audit covers every tracked `.py` file under `/Users/abhadra/github_copilot/aws-access-cli/scripts/` as read-only reference input for the migration story.

FCT-1 rule applied per file: **lib** means the file primarily wraps a domain mechanism that could be reused unchanged by an unrelated project.

Here, that means Athena execution, AWS SSO refresh, or generic query-running. **script** means it encodes `aws-access-cli`'s report-specific business rules, orchestration, query shapes, tenant
mapping, or output semantics.

Two implementation notes from the current reference tree:

- The story brief's older examples (`athena_runner/config.py`, `aws_clients.py`, `query_executor.py`, `result_downloader.py`, `sso_auth.py`) are no longer local files under this repo's `scripts/`
  tree; the current code imports those generic mechanisms from the external `athena_runner` package instead.
- For script-classified files, "Ported shared deps" names the `src/lib/*` module(s) the ported code should consume directly. `none` means the module stays a pure business-rule/helper module and should
  receive shared collaborators via its caller instead of importing them itself.

Legend for ported shared deps:

- `athena` = `src/lib/athena`
- `auth` = `src/lib/auth`
- `report_render` = `src/lib/report_render`
- `paths` = `src/lib/paths` (`PathResolver`, added during AAM-4)
- `query-catalog` = root `queries/athena/*.sql` catalog entry (not a `src/lib/*` import, but an explicit migration dependency worth recording here)

## Per-file classification table

| File | LOC | Verdict | FCT-1 rationale | Ported shared deps |
|---|---:|---|---|---|
| `athena_runner/adoption/__init__.py` | 3 | script | Package marker for the adoption-report business-logic namespace, not a reusable mechanism. | none |
| `athena_runner/adoption/metric_runner.py` | 102 | script | Runs one adoption metric and interprets its single-row result using this pipeline's adoption-report contract. | athena |
| `athena_runner/adoption/metric.py` | 60 | script | Defines the adoption metric shape and metadata used only by this report family. | none |
| `athena_runner/adoption/metrics/__init__.py` | 1 | script | Package marker for adoption metrics. | none |
| `athena_runner/adoption/metrics/attempts_unique_hhid.py` | 66 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/ebvs_sessions.py` | 90 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/ebvs_unique_hhid.py` | 89 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/guest_login_funnel_hhid.py` | 102 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/home_screen_unique_hhid.py` | 67 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/successful_vod_playback_hhid.py` | 67 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/successful_vod_playback_sessions.py` | 69 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/unique_guest_session.py` | 81 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/unique_hh_no_vsf.py` | 82 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/vod_playback_attempt_sessions.py` | 68 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/vsf_sessions.py` | 69 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/metrics/vsf_unique_hhid.py` | 67 | script | Encodes one named adoption metric's business definition. | query-catalog |
| `athena_runner/adoption/month_chunks.py` | 66 | script | Splits adoption-report periods the way this pipeline wants to backfill/report them; it is not a cross-project date utility. | none |
| `athena_runner/adoption/period_report_store.py` | 123 | script | Writes and merges this report family's period-grain output shape. | report_render, paths |
| `athena_runner/adoption/registry.py` | 144 | script | Registers this pipeline's adoption metrics and their names/order. | none |
| `athena_runner/adoption/report_store.py` | 157 | script | Writes and merges this report family's daily/month-file output shape. | report_render, paths |
| `athena_runner/position_report/__init__.py` | 1 | script | Package marker for position-report business logic. | none |
| `athena_runner/position_report/derive.py` | 273 | script | Derives Shaka 1xxx position-report fields from debug-event rows; the derivation rules are report-specific business logic. | none |
| `athena_runner/queries/__init__.py` | 1 | script | Package marker for this pipeline's Athena query shapes. | none |
| `athena_runner/queries/base.py` | 47 | script | Base abstraction for this pipeline's catalog-bound query definitions, not for generic Athena execution. | query-catalog |
| `athena_runner/queries/error_1xxx_session_ids.py` | 77 | script | Defines a report-specific Athena query shape. | query-catalog |
| `athena_runner/queries/incomplete_no_destroy_session_ids.py` | 108 | script | Defines a report-specific Athena query shape. | query-catalog |
| `athena_runner/queries/params.py` | 38 | script | Validates/holds parameter shapes only for this pipeline's query set. | none |
| `athena_runner/queries/playback_outcome.py` | 69 | script | Defines a report-specific Athena query shape. | query-catalog |
| `athena_runner/queries/registry.py` | 56 | script | Registers this pipeline's query names and classes. | query-catalog |
| `athena_runner/queries/session_debug_events.py` | 130 | script | Defines a report-specific Athena query shape. | query-catalog |
| `athena_runner/shaka_errors/__init__.py` | 9 | script | Package marker for Shaka error report logic. | none |
| `athena_runner/shaka_errors/column_merge.py` | 45 | script | Merges Shaka-error output columns according to this report family's semantics. | none |
| `athena_runner/shaka_errors/constants.py` | 25 | script | Encodes default Shaka error-code sets for this pipeline's reports. | none |
| `athena_runner/shaka_errors/query.py` | 164 | script | Defines Shaka-error report query shapes and parameters. | query-catalog |
| `athena_runner/shaka_errors/runner.py` | 110 | script | Runs a Shaka-error query and interprets the downloaded CSV as this report family's error-count mapping. | athena |
| `athena_runner/tenants.py` | 127 | script | Maps tenant codes to this pipeline's database/table naming and defaults; it is deployment/report specific, not a reusable Athena mechanism. | none |
| `refresh_aws_sso.py` | 77 | lib | Standalone CLI around AWS SSO credential refresh, a pure auth-domain mechanism with no `aws-access-cli` business rules. | auth |
| `run_adoption_gap_analysis_report.py` | 484 | script | Gap-analysis CLI with local extra metrics beyond the production adoption report. | auth, athena, report_render, paths |
| `run_adoption_gap_analysis_session_report.py` | 488 | script | Pipeline-specific session-grain gap-analysis CLI with local reconciliation logic. | auth, athena, report_render, paths |
| `run_adoption_report.py` | 520 | script | Entry point for the adoption household report; orchestration stays local even though mechanisms should be delegated. | auth, report_render |
| `run_adoption_session_report.py` | 528 | script | Entry point for the adoption session report; orchestration stays local even though mechanisms should be delegated. | auth, report_render |
| `run_athena_query.py` | 221 | lib | Generic "run a registered Athena query and save the CSV" utility, i.e. reusable query execution rather than report logic. | athena, auth, report_render |
| `run_daily_reports.py` | 531 | script | Pipeline-specific daily schedule/orchestration over six sub-reports and tenant fan-out. | auth |
| `run_guest_session_report.py` | 542 | script | Operator entry point for the guest-session report; output semantics and orchestration are pipeline-specific. | auth, report_render |
| `run_historical_backfill.py` | 427 | script | Pipeline-specific backfill orchestrator over this report set, dates, and tenant fan-out. | auth |
| `run_historical_period_reports.py` | 517 | script | Pipeline-specific historical period orchestrator over this report set and date math. | auth |
| `run_incomplete_no_destroy_investigation.py` | 289 | script | Investigation flow for this pipeline's specific "incomplete no destroy" adoption-gap question. | auth, athena, report_render, paths |
| `run_monthly_reports.py` | 549 | script | Pipeline-specific monthly schedule/orchestration over the report set. | auth |
| `run_shaka_1xxx_position_report.py` | 415 | script | Operator entry point for the Shaka 1xxx position report; the derivation and output are business-specific. | auth, report_render |
| `run_shaka_error_hhid_report.py` | 392 | script | Operator entry point for the Shaka household-error report; the output semantics are business-specific. | auth, report_render |
| `run_shaka_error_session_report.py` | 393 | script | Operator entry point for the Shaka session-error report; the output semantics are business-specific. | auth, report_render |
| `run_weekly_reports.py` | 538 | script | Pipeline-specific weekly schedule/orchestration over the report set. | auth |

## Migration consequences

### Clear lib/mechanism consumers

The only current in-repo files that are clean FCT-1 **lib** matches are:

- `refresh_aws_sso.py` → should become a thin CLI over `src/lib/auth`
- `run_athena_query.py` → should become a thin CLI over `src/lib/athena` plus catalog lookup

Everything else stays local to `src/pipelines/aws-access-cli/` because it answers `aws-access-cli`-specific reporting questions even when it relies on shared mechanisms underneath.

### Business-logic groupings for the port

- **Adoption family:** `athena_runner/adoption/**`, `run_adoption_report.py`, `run_adoption_session_report.py`, both adoption gap-analysis CLIs, and the historical/daily/weekly/monthly orchestrators
  that call them.
- **Shaka error family:** `athena_runner/shaka_errors/**`, `run_shaka_error_hhid_report.py`, `run_shaka_error_session_report.py`.
- **Position family:** `athena_runner/position_report/**`, `run_shaka_1xxx_position_report.py`.
- **Cross-family pipeline orchestration:** `run_daily_reports.py`, `run_weekly_reports.py`, `run_monthly_reports.py`, `run_historical_backfill.py`, `run_historical_period_reports.py`.
- **Pipeline-local extras outside the main three families:** `run_incomplete_no_destroy_investigation.py`, `run_adoption_gap_analysis_report.py`, `run_adoption_gap_analysis_session_report.py`, and
  `athena_runner/tenants.py`.

## Live crontab entries to feed AAM-5

Source: `aws-access-cli/docs/usage.md` §11 "Scheduling with cron".

```cron
0 6 * * * cd /path/to/aws-access-cli/scripts && \
    ../.venv/bin/python3 run_daily_reports.py --date "$(date -v-1d +\%Y-\%m-\%d)" \
    >> /path/to/aws-access-cli/logs/cron_daily_reports.out 2>&1

0 7 * * 1 cd /path/to/aws-access-cli/scripts && \
    ../.venv/bin/python3 run_weekly_reports.py --week "$(date -v-7d +\%Y-\%m-\%d)" \
    >> /path/to/aws-access-cli/logs/cron_weekly_reports.out 2>&1

0 22 * * * [ "$(date -v+1d +\%d)" = "01" ] && \
    cd /path/to/aws-access-cli/scripts && \
    ../.venv/bin/python3 run_monthly_reports.py --month "$(date +\%Y-\%m)" \
    >> /path/to/aws-access-cli/logs/cron_monthly_reports.out 2>&1
```
