# Logging framework rollout — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` + `PYTHON_DESIGN.md`. After each task: set `SHA:` on the task
> line + tick the box, update the story status summary, add one line to your backlog/session-log file.

---

## LFR-1 — Build the `init_logging()` bootstrap

**Files to change / create:**
- `src/lib/logging/bootstrap.py` — new. Composes `src/lib/logging/setup.py`'s `setup_logging()` and `context.py`'s `bind_fcid`/`FcidLogFilter`; does not duplicate their logic.
- `src/lib/logging/setup.py` — extend the format string to include `%(fcid)s`; attach a module-level `FcidLogFilter` instance to every handler `setup_logging()` creates (not to the root logger — see
  `context.py`'s own docstring on why a filter on a parent logger is not consulted for child-logger records before they propagate).
- `src/lib/logging/redact.py` — new. `redact_params(params: dict, allow_keys: set[str]) -> dict`, per FCID-1's original spec: drop/`***`-mask any key not in `allow_keys`.
- `tests/lib/logging/test_bootstrap.py` — new.
- `tests/lib/logging/test_redact.py` — new.

**What to implement:**

1. `init_logging(entry_point_slug: str, *, level: str = "INFO", to_file: bool = True) -> str`:
   - Generates one FCID using FCID-1's exact format (`f"{entry_point_slug}-{utc_timestamp:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"`).
   - Calls `setup_logging(level=level, to_file=to_file)`.
   - Calls `bind_fcid(fcid)`.
   - Returns the FCID (callers that need to pass it to a subprocess env var, per FCID-1's flagged-open cross-process question, can do so explicitly — this function does not solve that).
2. Update `setup_logging()`'s format string to `"%(asctime)s [%(levelname)s] [%(name)s] [fcid=%(fcid)s] %(message)s"` and attach `FcidLogFilter()` to each handler it builds, so every record gets
   `record.fcid` set (defaulting to `"no-fcid"` for any logger `init_logging()` wasn't the entry point for — e.g. third-party library logs).
3. `redact_params(params, allow_keys)`: returns a new dict; keys in `allow_keys` pass through unchanged, all others become `"***"`. Raise on `allow_keys` being empty (an all-redacted call is almost
   certainly a mistake, not an intentional one) rather than silently producing an all-`"***"` dict.

**Tests (no network, no real external services):**
- `test_init_logging_binds_and_returns_fcid` — calling `init_logging("test-entry")` returns a string matching the FCID format, and `current_fcid()` returns the same value afterward.
- `test_init_logging_log_record_carries_fcid` — using `caplog`, a `logger.info(...)` call after `init_logging()` has a record with `record.fcid` equal to the bound FCID.
- `test_init_logging_idempotent_handlers` — calling `init_logging()` twice in one process does not double the handler count on the root logger (relies on `setup_logging()`'s existing `force=True`).
- `test_redact_params_masks_non_allowed_keys` — a dict with 3 keys, 1 allow-listed, returns that key unchanged and the other two as `"***"`.
- `test_redact_params_empty_allow_keys_raises` — `redact_params({"a": 1}, set())` raises `ValueError`.

**Commit:** `feat(logging): add init_logging bootstrap + redact_params`

---

## LFR-2 — Minimum logging contract + apply to Athena adapter and pipeline business logic

**Files to change / create:**
- `docs/refactor/logging-and-correlation-id.md` — append a new "## Minimum logging contract" section (see spec below).
- `src/lib/athena/adapter.py` — add the happy-path calls the contract requires; it already has `_logger.warning` for throttle-retry, do not duplicate that case.
- `src/pipelines/aws_access_cli/adoption.py`, `shaka_errors.py`, `position_report.py` — add a module logger (`logging.getLogger(__name__)`) where none exists; log per the contract.
- `tests/lib/athena/test_adapter.py`, `tests/pipelines/aws_access_cli/test_adoption.py` (+ siblings for the other two modules) — extend existing test files with `caplog`-based assertions; do not
  create new test files if one already covers the module.

**What to implement:**

1. Minimum logging contract (write into `logging-and-correlation-id.md`, then apply):
   - **Run start** (`INFO`) — once, immediately after `init_logging()`: entry-point slug + any top-level args (date, tenant list) relevant to reproducing the run.
   - **External-call start** (`DEBUG`) — immediately before any Athena/network/subprocess call: which call, key non-sensitive params (via `redact_params`).
   - **External-call success** (`INFO`) — immediately after: duration (ms), row/result count if applicable.
   - **External-call failure** (`ERROR`, via `logger.exception` inside an `except`) — exactly once per failure, at the layer that first catches it; a layer that only re-raises does not also log (this
     is what was causing the duplicate bare-`.error()`-plus-traceback shape found in the 2026-10-04 cron investigation — fix that duplication here too, in `vendor/athena-mcp-server`'s `sso_auth.py` is
     out of scope since it's a pinned submodule, but `src/lib/athena/adapter.py`'s own call sites must not repeat it).
   - **Run end** (`INFO`) — once, at the entry point: overall result (success/fail count across tenants/reports).
2. Apply to `src/lib/athena/adapter.py`: log external-call start/success/failure around its `AthenaQueryExecutor.run()`/`ResultDownloader` calls, per the contract.
3. Apply to the three `aws_access_cli` business-logic modules: each logs "processing tenant X, report Y" at `INFO` on entry and "produced N rows" at `INFO` on return.

**Tests (no network, no real external services):**
- `test_adapter_logs_query_success_with_duration` — mocked executor returns a result; `caplog` shows one `INFO` record with a `duration_ms` field.
- `test_adapter_logs_query_failure_once` — mocked executor raises; `caplog` shows exactly one `ERROR`-level record for that failure, not two.
- `test_adoption_logs_run_start_and_row_count` (+ one per sibling module) — `caplog` shows an `INFO` record naming the tenant and the report, and a second with the row count.

**Commit:** `feat(logging): apply minimum logging contract to athena adapter + pipeline business logic`

---

## LFR-3 — Wire the bootstrap into every `aws_access_cli` entry point; separate preview output

**Files to change / create:**
- `src/pipelines/aws_access_cli/scripts/run_daily_reports.py`, `run_weekly_reports.py`, `run_monthly_reports.py`, `run_historical_backfill.py`, `run_historical_period_reports.py`, and every other
  `run_*.py` under that directory (15 files total per the 2026-10-04 inventory) — call `init_logging(entry_point_slug=...)` as the first statement in `main()`, before any argument parsing that could
  itself fail and go unlogged.
- `src/pipelines/aws_access_cli/schedule.py` — no code change expected (its `LOGGER.exception`/`LOGGER.error` calls already exist; they just need a configured handler upstream), but confirm this with
  a test, do not assume.
- `src/pipelines/aws_access_cli/scripts/common.py` — gate the `print(render_summary(...))` preview calls behind an explicit `--preview` flag (default off) each `run_*.py` already exposes via
  `argparse`, or add one where it doesn't exist yet; cron invocations (per `run_daily_reports.py`'s `build_argv`) must not pass it.
- `tests/pipelines/aws_access_cli/test_schedule.py` (or wherever existing coverage lives) — extend.

**What to implement:**

1. Add `init_logging(entry_point_slug="aws-access-cli-<report-name>")` as the first line of each `run_*.py`'s `main()`, matching the per-script report name (e.g. `"aws-access-cli-daily-reports"`).
2. Gate preview-table `print()` calls behind an opt-in flag, off by default, so a scheduled/cron run never emits them; an interactive/manual run can still pass the flag to see the preview.
3. Confirm (with a test, not just reasoning) that `schedule.py`'s existing `LOGGER.exception`/`LOGGER.error` calls now produce a properly formatted, single (not duplicated) log line once a real
   `run_*.py` entry point is exercised end-to-end with `init_logging()` wired in.

**Tests (no network, no real external services):**
- `test_run_daily_reports_calls_init_logging` — `main()` is run with the entry-point bootstrap mocked; assert it was called exactly once, before `run_for_all_tenants`.
- `test_run_daily_reports_preview_off_by_default` — mocked sub-report runner; assert `render_summary`/`print` is not invoked unless the preview flag is passed.
- `test_schedule_failure_logs_once_with_fcid` — a sub-report raising an exception, with `init_logging()` actually called first, produces exactly one `caplog` `ERROR` record carrying the bound FCID.

**Commit:** `feat(pipeline): wire init_logging into aws-access-cli entry points; gate preview output`

---

## LFR-4 — Binding "Logging" checklist section + `CONTEXT.md` update

**Files to change / create:**
- `docs/refactor/code-review-checklist.md` — new numbered section (after the existing "4. FCID / cross-cutting ambient-context correctness" section, renumbering subsequent sections), same
  one-box-per-trigger shape.
- `CONTEXT.md` — update the `src/lib/logging/context.py` bullet (currently ends "...remain deferred future work, not yet owned by any `docs/plan/` task") to point at this story instead; add one new
  bullet for `docs/plan/logging-framework/` itself, in the same style as other in-progress story bullets (e.g. `pipeline-migration`'s).

**What to implement:**

1. New checklist section, e.g.:
   ```markdown
   ## 7. Logging coverage (`logging-and-correlation-id.md`'s minimum contract)

   - [ ] Any new entry point (`run_*.py` `main()`, a tool's CLI `main()`, an investigation script's top-level call) calls `init_logging()` as its first statement, not `setup_logging()` /
         `logging.basicConfig()` directly.
   - [ ] Any new external-call site (Athena/network/subprocess) logs call-start at `DEBUG` and call-success at `INFO` with a duration, per the minimum contract — not just a failure path.
   - [ ] Any new `except` block that logs a failure does so exactly once, at the layer that first catches it — a re-raising layer does not also log, to avoid the duplicate-bare-message-plus-traceback
         shape found in the 2026-10-04 cron log investigation.
   - [ ] Any new log line carrying request/query parameters uses `redact_params()` rather than logging an opaque param dump.
   ```
2. `CONTEXT.md` edit: replace the stale "not yet owned by any `docs/plan/` task" clause with a pointer to `docs/plan/logging-framework/`, and add a new bullet describing this story's existence and
   current task progress (update again at story close, per `docs/plan/README.md`'s own "After each task" convention).

**Tests:** N/A — docs-only task.

**Commit:** `docs(logging): add binding logging checklist section; update CONTEXT.md`

---

## LFR-5 — Coordination notes in unretrofitted consumers

**Files to change / create:**
- `investigations/ctap-smvod/` — its own `README.md` or equivalent top-level doc (check `docs/plan/pipeline-migration/ctap-smvod-investigation-migration/README.md` first; if that story is already
  archived, the note goes in the archived copy per this project's own archiving convention — do not resurrect a closed story to add it).
- Any other `__main__` entry point identified by the 2026-10-04 inventory that still has no `init_logging()` call and no existing story tracking it (`scripts/dev/*`, `scripts/athena/*` beyond the 4
  that already call `setup_logging()` directly — those 4 get a one-line note that they should migrate to `init_logging()` next time they're touched, not a full rewrite here).

**What to implement:**

1. One dated line per unretrofitted consumer, in the same style as this project's existing "Coordination without ownership" notes (e.g. `pipeline-migration/README.md`'s FCID coordination line):
   "2026-10-XX: this consumer does not yet call `src/lib/logging/bootstrap.py`'s `init_logging()`; see `docs/plan/logging-framework/` — coordination record only, not implemented here."
2. Do not modify any of these consumers' actual code or tests in this task — notes only.

**Tests:** N/A — docs-only task.

**Commit:** `docs(logging): add coordination notes to unretrofitted logging consumers`
