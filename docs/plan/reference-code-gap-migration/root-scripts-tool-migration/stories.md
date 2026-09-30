# root scripts migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## RSC-1 — audit + per-file classification + FCT-6 overlap check

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read `/Users/abhadra/github_copilot/scripts/disk_usage.py`, `generate_scripts_registry.py`, `reflow_markdown.py`, `update_athena_table_ddl_knowledge.py`.
2. Confirm or refine `spec.md` §8's classification — state the FCT-1 test result explicitly per file.
3. Read `functional-code-taxonomy`'s FCT-6 spec and `ih-trace-lab`'s existing `scripts/dev/generate_scripts_registry.py` (if it exists yet); determine whether `github_copilot`'s
   `generate_scripts_registry.py` is already fully superseded by that tooling. Record the finding either way — do not silently port a second copy without checking.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(root-scripts-tool-migration): audit scripts, classify lib vs. business logic, check FCT-6 overlap`
