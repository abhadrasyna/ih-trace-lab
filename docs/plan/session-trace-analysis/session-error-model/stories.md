# Session error model (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

Constraint for every task: no tenant code or id hardcoded; no network in tests; fixtures use placeholder ids; no new persistent long table.

---

## EM-1 — First-error library

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_error_model.py` — pure `first_error(...)` plus small loaders that take paths.
- `investigations/ctap-smvod/tests/test_session_error_model.py`.

**What to implement:**

1. Candidates per session: (a) mDRM non-2xx rows (mdrmfe `http.status_code` on `drmAuthToken.sessionId`; LRM and CDM via `fcid`), reusing the readers in `scripts/lib/drm_exports.py` and the
   `mdrm_quality_failures` logic in `analyze_mdrm_quality.py` (import, do not copy); (b) the first non-empty `errorcode` in `debug_states.csv` (rows with `eventid = PLAYER_ERROR` have an EMPTY
   `state`), ordered by `datetime`; the flat error eventdata supplies the same code for cross-checking.
2. Return one row per session: `first_error_code`, `first_error_source` (`mdrmfe`, `lrm`, `cdm`, `debug`, `none`), `first_error_time`, `all_error_codes` (every code seen, ordered by time), plus
   `first_debug_code` (always the debug code, whatever the winner) and `mdrm_failure` (layers and statuses, for example `mdrmfe:403+lrm:400+cdm:400`, empty when none).
3. Rule: earliest by time; on equal time (within 2 s, see 5) or one-source sessions use the priority mDRM, then debug, then none. Blank-`sessionId` failed setups are never returned (stage 0, handled
   by the funnel).
4. Fail loudly on a missing required column; no bare `except`.
5. **mDRM time and join.** The mDRM exports have no timestamp column; the request time is the `fcId` hex prefix read as unix seconds (validated on ZA 2026-10-24, see `prompt.md`). Timestamps are
   compared with a 2 s tolerance. LRM and CDM rows join to a session through the mdrmfe `fcid`; count rows that do not join and report the count, never drop them silently. Read every part file
   (`export_paths`), because the pipeline does not combine the mDRM parts.
6. **Code spaces.** An mDRM HTTP status and a player error code are different code spaces. `first_error_code` keeps the winning source's own value; never compare or merge codes across sources.
   `first_debug_code` is the debug-side code that the crosstab keeps.
7. **Device attributes per session** (generic, no code-specific logic): `is_wv`, `drm_type`, `cdm_make`, `cdm_model`, `cdm_security_level` and `device_source` (`setupsession`, `mdrmfe`, `none`).
   `is_wv` and the user agent come from `raw_user_agent`/`Platform` in `output/<TENANT>/<date>_setupsession_with_outcome.csv` through `scripts/lib/webview.py::is_wv` (mdrmfe `http.user_agent` is the
   fallback; the two agreed on 1,746 of 1,746 comparable ZA 2026-10-24 sessions). `drm_type` and the CDM fields come from mdrmfe and CDM via `fcid` and exist only for sessions that reached mDRM.
   Unknown stays blank, never `false` or "unknown".

**Tests:** `test_earliest_error_wins`, `test_mdrm_wins_on_equal_time`, `test_debug_only_session`, `test_no_error_is_none`, `test_all_codes_kept_in_time_order`, `test_missing_column_raises`,
`test_code_spaces_not_mixed`, `test_fcid_prefix_time`, `test_lrm_cdm_join_via_mdrmfe_fcid`, `test_unjoined_rows_counted`, `test_unknown_device_stays_blank`, `test_device_falls_back_to_mdrmfe_ua`.

**Commit:** `feat(ctap-smvod): add session first-error model`

---

## EM-2 — Cross-day outcome classifier

**Files to change / create:**
- `queries/athena/ctap-smvod-session-outcome.sql` (slug `ctap-smvod-session-outcome`; follow `docs/guides/query-catalog.md`): one row per `parent_session_id` that has a `REQUEST_VIEWING` row dated
  `{{date}}`, aggregating that session's rows over `{{date}}` .. `{{date}}` + look-ahead days: `has_play`, `play_endreason`, `request_endreason`, `has_destroy`, `has_buffering`, `has_player_error`,
  `first_day`, `last_day`, `last_event_type`, `last_endreason`.
- `investigations/ctap-smvod/scripts/run_athena_session_outcome.py` — thin exporter to `data/athena/<TENANT>/<date>_session_outcome.csv` (`--tenant`, `--date`, `--lookahead-days`, default 2).
- `investigations/ctap-smvod/scripts/lib/session_outcome.py` — pure `classify_outcome(row)` and `outcome_counts(rows)`.
- `investigations/ctap-smvod/tests/test_session_outcome.py`.

**What to implement:** the order and definitions in `prompt.md`; set `crossed_midnight` when `first_day != last_day`; the two no-end classes carry `last_event_type` and `last_endreason`. The existing
outcome query and outputs stay unchanged.

**Tests:** `test_each_outcome_class`, `test_vsf_not_counted_as_no_end`, `test_crossed_midnight_success_flagged`, `test_order_first_match_wins`, `test_missing_column_raises`.

**Baseline (ZA 2026-10-24, live 2026-10-26, look-ahead 2 days):** 3,805 = success 1,187 + VSF 2,088 + EBVS 214 + VPF 80 + VPT 227 + buffering_no_end 3 + startup_no_followup 6.

**Commit:** `feat(ctap-smvod): add cross-day session outcome classifier`

---

## EM-3 — Cross-check and reconciliation

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_outcome.py` — pure `reconcile(per_session_counts, report_row)` returning per-class differences.
- `investigations/ctap-smvod/scripts/reconcile_session_outcome.py` — argparse (`--tenant`, `--date`, `--report-csv`); prints and writes
  `output/<TENANT>/session-presence/csv/<date>_outcome_reconcile.csv`.
- Matching tests.

**What to implement:** compare the per-session split with the adoption report row for the date (`VOD-Playback-Attempt-Sessions`, `Successful-VOD-Playback-Sessions`, `VSF-Sessions`, `EBVS-Sessions`;
residual = attempts − the other three), print the difference per class and record the export time (`max(ingest_timestamp)` of the rows) so a gap can be read as late ingestion. Cross-check
`first_error_code` against `<date>_error_report_1xxx_6xxx.csv` for the sessions in it, without recomputing 1xxx/6xxx logic.

**Baseline:** report 3,803 / 1,188 / 2,086 / 215 / residual 314 against live 3,805 / 1,187 / 2,088 / 214 / residual 316.

**Tests:** `test_reconcile_reports_per_class_difference`, `test_reconcile_zero_difference`.

**Commit:** `feat(ctap-smvod): reconcile session outcomes with adoption report`

---

## EM-4 — Outcome × first-error-code report and charts

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_outcome.py` — pure `outcome_error_crosstab(outcomes, first_errors)` returning counts per (outcome, first_error_code) and per-class `with_code` share.
- `investigations/ctap-smvod/scripts/analyze_outcome_error_codes.py` — argparse (`--tenant`, `--date`); joins the EM-2 per-session outcome export with the EM-1 first error and writes
  `output/<TENANT>/session-presence/csv/<date>_outcome_error_codes.csv` plus a markdown table.
- Matching tests in `tests/test_session_outcome.py`.
- `investigations/ctap-smvod/scripts/chart_outcome_error_codes.py` — thin renderer over the CSV using `src/lib/charts/` (`render_stacked_bar`, `render_bar`, `output.write_chart_png`), following
  `docs/guides/chart-guidelines.md`; flag `--skip-charts` on the analysis script. Only existing shared chart helpers are used (no new heatmap).
- `investigations/ctap-smvod/tests/test_chart_outcome_error_codes.py`.

**Charts** (PNG to `output/<TENANT>/charts/`, no network; none is specific to an error code):
1. `<date>_outcome_attempts.png` — one stacked bar of attempts by the 7 classes, counts and %, green for success and red for failures, export time in the footnote.
2. `<date>_outcome_first_error_source.png` — 100% stacked bar per outcome class split by first-error source (`mdrmfe`, `lrm`, `cdm`, `debug`, `none`); `none` in grey so "no error observed" is not read
   as a source.
3. `<date>_outcome_mdrm_reach.png` — stacked bar per outcome class: no mdrmfe row, mdrmfe 2xx, mDRM non-2xx.
4. `<date>_outcome_by_device.png` — non-success rate per device attribute (`is_wv`, DRM type, CDM security level), each with a `not available` bucket and the session count beside it. No heatmap and no
   per-code chart. Every chart states which sources were included (debug only when mDRM exports for the date are absent).

**What to implement:** all seven classes, not only the failures. The crosstab of outcome × `first_debug_code` (`(none)` for no debug code) is written to the CSV and markdown only, not charted;
`mdrm_failure` is a separate column so mDRM failures never move a session between code groups. Report the first-error source alongside the code and flag a debug-only first error where mDRM exports for
the date are absent. Also write the outcome × mDRM status table (sessions with an mdrmfe row, sessions with a non-2xx, statuses by source) and the outcome × device-attribute tables, as in `prompt.md`.
`(none)` means no debug error and no mDRM non-2xx, with the export-completeness caveat in the markdown. Device attributes come from EM-1 item 7; no split is specific to one code. Where the
3014/3015/3016 `subcategory_events.csv` exists, an optional join may add `cdm_make`, `cdm_model` and `license_status` without recomputing it. Device rates show associations only, not causes; per-model
rates stay out of the report until several days are combined.

**Tests:** `test_missing_device_is_own_bucket`, `test_mdrm_failure_does_not_change_debug_code_group`, `test_crosstab_counts_per_class_and_code`, `test_none_bucket_for_sessions_without_code`,
`test_success_with_code_counted`, `test_with_code_share`, `test_first_error_source_counts`, `test_mdrm_reach_counts`, `test_device_rate_per_attribute`, `test_charts_write_nonempty_pngs`,
`test_none_bucket_is_grey`.

**Baseline (ZA 2026-10-24, live 2026-10-26):** see "Evidence — first error code by outcome" and "Evidence — mDRM correlation" in `prompt.md`.

**Commit:** `feat(ctap-smvod): report outcome by first error, mDRM reach and device`

---

## EM-5 — Docs

**Files to change:** `investigations/ctap-smvod/docs/usage.md`, `CONTEXT.md` (What Exists), `session-presence-funnel/stories.md` (PF-8 points here).

**What to implement:** document the scripts, the definitions and the late-ingest caveat; state that per-session counts are the headline and that adoption-report counts lag. Also document the
`fcId`-prefix time proxy for the mDRM exports, the code-space rule (debug code against mDRM status), that the mDRM parts must be read by part, and that device attributes are reported generically per
outcome (associations, not causes).

**Commit:** `docs(ctap-smvod): document session error model`
