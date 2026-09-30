# root investigations migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## RIN-1 — audit + per-file classification + Jira-script reconciliation

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read all 10 files under root `/Users/abhadra/github_copilot/investigations/scripts/` (`check_bein.py`, `check_player_version.py`, `check_session.py`, `extract_comments_bulk.py`,
   `extract_jira.py`, `extract_jira2.py`, `extract_search.py`, `generate_drm_flow_report.py`, `get_final_answer.py`, `sign_jws_json.py`).
2. Confirm or refine `spec.md` §5's classification — state the FCT-1 test result explicitly per file.
3. Compare `extract_jira.py` (45 LOC) and `extract_jira2.py` (75 LOC) line-by-line; decide which one becomes the single ported target (or whether a merge is needed) and state the reason.
4. Confirm which 2 files (`generate_drm_flow_report.py`, `sign_jws_json.py`) stay blocked on `src/lib/mpd/`/`src/lib/crypto_signing/` per epic `README.md`'s promotion decisions, and which 8 are
   unblocked.
5. Confirm the `investigations/legacy-adhoc/` target-folder reasoning in this story's own `prompt.md` still holds on closer re-read of all 10 files (i.e. no shared campaign narrative was missed).

**Tests:** none — audit/docs-only task.

**Commit:** `docs(root-investigations-migration): audit scripts, classify lib vs. business logic, reconcile Jira extractors`
