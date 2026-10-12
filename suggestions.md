# Session Efficiency Suggestions — Ranked by Recurrence

> Maintained by `.github/skills/session-close/SKILL.md` Step 4b. `Count` = number of sessions where this exact root cause recurred. Sorted by `Count` descending. Do not hand-edit `Count`; the skill
> owns it.

| Count | Slug | Suggestion | Category | First seen | Last seen |
|---|---|---|---|---|---|
| 41 | update-context-for-new-files | Update CONTEXT.md before commit whenever a session adds a new persistent repo file. | protocol-compliance | 2026-09-27 | 2026-10-12 |
| 32 | avoid-mid-session-rereads | Reuse already-loaded file context instead of re-reading the same file mid-session unless it changed. | token-efficiency | 2026-09-27 | 2026-10-11 |
| 30 | state-plan-before-editing | State the one-sentence plan before the first edit, even when the next task seems obvious from story order. | protocol-compliance | 2026-09-30 | 2026-10-12 |
| 25 | wait-for-explicit-go-ahead-before-editing | Wait for explicit reply after stating the plan, before creating/committing when approval required. | protocol-compliance | 2026-09-27 | 2026-10-10 |
| 24 | re-read-context-on-resumed-task-segments | On each resumed autopilot segment, re-open CONTEXT.md and state `CONTEXT.md ✓`. | protocol-compliance | 2026-10-02 | 2026-10-08 |
| 19 | confirm-target-files-before-starting | When destination files aren't named, confirm which files change before creating new modules/tests. | protocol-compliance | 2026-09-29 | 2026-10-04 |
| 18 | prefer-scoped-file-reads-over-full-cat-dumps | Prefer `view_range`/`sed -n`/`grep`/summaries over full `cat` dumps once target section is known. | token-efficiency | 2026-09-29 | 2026-10-10 |
| 14 | avoid-broad-filesystem-finds | Use repo-local `glob`/known paths, not broad `find`/repo-wide `grep -r` probes. | token-efficiency | 2026-09-27 | 2026-10-11 |
| 13 | state-context-md-checkmark-explicitly | State `CONTEXT.md ✓` verbatim in the first response, not just read the file silently before coding. | protocol-compliance | 2026-09-28 | 2026-10-12 |
| 13 | edit-tool-over-inline-python-rewrite | Use the `edit` tool, not inline python rewrites; reflow can break string asserts. | protocol-compliance | 2026-10-07 | 2026-10-10 |
| 6 | reflow-md-before-commit | Run `python -m scripts.dev.reflow_md` on edited markdown before `git commit` so md-line-length pre-commit does not fail. | commit-hygiene | 2026-10-07 | 2026-10-12 |
| 6 | write-and-run-tests-before-commit | Add happy-path/edge-case tests for new public fns, run green before commit; missing harness isn't a stop. | protocol-compliance | 2026-09-29 | 2026-10-04 |
| 5 | confirm-commit-sha-after-commit | After each commit, surface the resulting SHA in the user-facing summary instead of relying on git log output alone. | commit-hygiene | 2026-09-29 | 2026-10-02 |
| 3 | no-inline-python-for-data-analysis | Put CSV analysis in a permanent scripts/ file (check SCRIPTS.md first), not inline python. | protocol-compliance | 2026-10-10 | 2026-10-11 |
| 3 | use-edit-tool-not-sed-i | Use the edit tool for file changes, not `sed -i` or `cat >>` heredocs via bash. | protocol-compliance | 2026-10-10 | 2026-10-11 |
| 3 | avoid-tmp-for-commit-message-workaround | Never use `/tmp` to work around heredoc quoting for commit messages; fix quoting or use a repo path. | protocol-compliance | 2026-10-06 | 2026-10-07 |
| 3 | context-md-not-read-on-query-sessions | Read and acknowledge CONTEXT.md at session start even for pure Q&A sessions with no code touched. | protocol-compliance | 2026-09-30 | 2026-10-04 |
| 2 | avoid-tmp-for-command-output-logs | Redirect long-run command output to a repo path (e.g. logs/), never /tmp. | protocol-compliance | 2026-10-07 | 2026-10-11 |
| 2 | search-repo-tooling-before-live-athena-query | Before a live Athena/Lightstep query, grep `src/pipelines/` and `config/` for helpers. | protocol-compliance | 2026-10-08 | 2026-10-10 |
| 2 | avoid-repeated-read-agent-polling | After launching a sub-agent, wait for completion instead of polling `read_agent` for status-only updates. | token-efficiency | 2026-10-04 | 2026-10-04 |
| 1 | review-staged-files-before-commit | Run `git diff --cached --stat` before commit and tell the user about pre-staged files that will be swept in. | commit-hygiene | 2026-10-12 | 2026-10-12 |
| 1 | no-row-level-ids-in-head-output | Inspect CSV headers only (`head -1`); never print data rows with deviceId/messageid. | token-efficiency | 2026-10-11 | 2026-10-11 |
| 1 | re-view-section-after-reflow-before-edit | After reflowing markdown, re-view target lines before editing; reflow breaks old_str. | token-efficiency | 2026-10-10 | 2026-10-10 |
| 1 | verify-edit-boundaries-after-markdown-edit | After an `edit` touching headings, view the edited region so dropped headings are caught at once. | commit-hygiene | 2026-10-10 | 2026-10-10 |
| 1 | no-placeholder-message-or-no-verify-amend | Never probe the pre-commit hook with a placeholder message or amend with `--no-verify`; re-run the hook. | commit-hygiene | 2026-10-09 | 2026-10-09 |
| 1 | reflow-md-and-avoid-gnu-timeout-before-commit | Run `scripts/dev/reflow_md.py` after the last markdown edit; no GNU `timeout` on macOS. | commit-hygiene | 2026-10-09 | 2026-10-09 |
| 1 | athena-mcp-resolve-overrides-before-first-call | Before the first run_athena_sql, look up tenant overrides (config/tenants.yaml) and pass them. | protocol-compliance | 2026-10-08 | 2026-10-08 |
| 1 | verify-doc-examples-by-running-help | Run each documented command with `--help` or a dry run before committing usage examples. | protocol-compliance | 2026-10-07 | 2026-10-07 |
| 1 | state-context-md-ack-in-first-response | After reading CONTEXT.md, put the literal `CONTEXT.md ✓` in the first user-facing text. | protocol-compliance | 2026-10-07 | 2026-10-07 |
| 1 | validate-overwrite-safety-invariants-before-implementing | Before a script that overwrites files, state the "only touch our own files" rule. | protocol-compliance | 2026-10-07 | 2026-10-07 |
| 1 | check-write-targets-before-running | Before running a test suite or backfill, check what it writes and its CLI range semantics (--help). | protocol-compliance | 2026-10-07 | 2026-10-07 |
| 1 | isolate-untracked-files-before-precommit-stash | Before committing, stash unrelated untracked files so the hook's stash cycle skips them. | commit-hygiene | 2026-10-06 | 2026-10-06 |
| 1 | amend-local-only-commits-for-sha-backfill | For an unpushed commit followed by a SHA-backfill doc edit, use `git commit --amend` to fold it in. | commit-hygiene | 2026-10-02 | 2026-10-02 |
| 1 | minimize-context-in-subagent-delegation-prompts | When delegating to a self-extracting subagent, give a terse pointer, not a full summary. | token-efficiency | 2026-10-02 | 2026-10-02 |
| 1 | avoid-git-reset-hard-for-revert | Use `git revert` (new commit) not `git reset --hard`, which discards uncommitted changes too. | commit-hygiene | 2026-09-29 | 2026-09-29 |
| 1 | verify-commit-landed-after-precommit-stash | If pre-commit stashes unstaged files, re-check `git log -1` — a stash cycle can silently no-op it. | commit-hygiene | 2026-09-29 | 2026-09-29 |
| 1 | avoid-conflicting-parallel-file-ops | Do not run a destructive remove and a create for the same path in one parallel batch; sequence them. | token-efficiency | 2026-09-28 | 2026-09-28 |
