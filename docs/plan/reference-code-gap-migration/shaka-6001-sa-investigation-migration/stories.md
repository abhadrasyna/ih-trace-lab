# shaka-6001-sa-error-analysis migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## SHK-1 — audit + per-file classification

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read `/Users/abhadra/github_copilot/shaka-6001-sa-error-analysis/scripts/lib/athena_runner.py`, `lib/aws_sso.py`, `lib/user_agent_parser.py`, `query_daily_shaka_errors.py`,
   `query_session_shaka_errors.py`.
2. Confirm or refine `spec.md` §7's classification — state the FCT-1 test result explicitly per file.
3. Confirm the device/user-agent-identity accept-local decision (epic `README.md`) still holds — i.e. no second real consumer of `user_agent_parser.py`'s exact mechanism has appeared since the
   2026-09-30 audit.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(shaka-6001-sa-investigation-migration): audit scripts and classify lib vs. business logic`
