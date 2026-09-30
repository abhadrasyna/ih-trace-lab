# applauseInvestigation migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## APL-1 — audit + per-file classification

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table, appended to this file below the task spec or committed as a standalone `AUDIT.md` in this
folder (author's choice, state which in the commit message).

**What to implement:**

1. Re-read every file under `/Users/abhadra/github_copilot/applauseInvestigation/scripts/` (9 files: `analyze_applause_issues.py`, `analyze_athena_playback.py`, `analyze_har.py`,
   `analyze_lightstep_big_picture.py`, `analyze_lightstep_latency.py`, `analyze_smvod_sessions.py`, `epoch_to_utc.py`, `organize_reproduction_run.py`, `run_athena_debug_events.py`).
2. For each file, confirm or refine `spec.md` §6's classification (`lib candidate: <module(s)>` vs. `script: business-logic`) — state the FCT-1 "shared vs. specific" test result explicitly, not just
   cite the existing table.
3. Note which `src/lib/*` modules must exist first (`athena`, `csv_io`, `har`, `report_render`, `paths`) and confirm none of this project's files need a new module (per epic `README.md`'s promotion
   decisions — none apply here).

**Tests:** none — audit/docs-only task.

**Commit:** `docs(applause-investigation-migration): audit scripts and classify lib vs. business logic`
