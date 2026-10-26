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
2. Return one row per session: `first_error_code`, `first_error_source` (`mdrmfe`, `lrm`, `cdm`, `debug`, `none`), `first_error_time`, `all_error_codes` (every code seen, ordered by time).
3. Rule: earliest by time; on equal time or one-source sessions use the priority mDRM, then debug, then none. Blank-`sessionId` failed setups are never returned (stage 0, handled by the funnel).
4. Fail loudly on a missing required column; no bare `except`.

**Tests:** `test_earliest_error_wins`, `test_mdrm_wins_on_equal_time`, `test_debug_only_session`, `test_no_error_is_none`, `test_all_codes_kept_in_time_order`, `test_missing_column_raises`.

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

## EM-4 — Docs

**Files to change:** `investigations/ctap-smvod/docs/usage.md`, `CONTEXT.md` (What Exists), `session-presence-funnel/stories.md` (PF-8 points here).

**What to implement:** document the scripts, the definitions and the late-ingest caveat; state that per-session counts are the headline and that adoption-report counts lag.

**Commit:** `docs(ctap-smvod): document session error model`
