# mtn-zm-session-device-investigation migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## MZD-1 — audit + per-file classification

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read all 19 implementation files under `/Users/abhadra/github_copilot/mtn-zm-session-device-investigation/scripts/` (incl. `athena_runner/investigation_config.py`, `athena_runner/queries/*.py`,
   `athena_runner/tenants.py`, `athena_runner/time_window_utils.py`, `build_final_session_report.py`, `classify_session_outcomes.py`, `extract_error_codes_from_debug_events.py`,
   `extract_problematic_session_ids.py`, `generate_summary.py`, `run_athena_query.py`, `run_investigation_pipeline.py`, `summarize_final_session_report.py`, `verify_incomplete_no_destroy.py`).
2. Confirm or refine `spec.md` §2's classification — state the FCT-1 test result explicitly per file.
3. Confirm the Tier-2 (no new module) correction in this story's own `prompt.md` still holds — i.e. tenant/query-registry and session-outcome-classification logic remains business logic, not a missing
   shared mechanism, on closer re-read.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(mtn-zm-device-investigation-migration): audit scripts and classify lib vs. business logic`
