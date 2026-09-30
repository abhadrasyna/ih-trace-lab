# astro-events-household-report migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## AEH-1 — audit + per-file classification

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read `/Users/abhadra/github_copilot/astro-events-household-report/scripts/inspect_sample_keys.py` and `pivot_distinct_values.py`.
2. Confirm or refine `spec.md` §9's classification (`lib candidate: csv_io` for both) — state the FCT-1 test result explicitly.
3. Confirm no new `src/lib/*` module is needed (per epic `README.md`'s promotion decisions — none apply here).

**Tests:** none — audit/docs-only task.

**Commit:** `docs(astro-events-household-investigation-migration): audit scripts and classify lib vs. business logic`
