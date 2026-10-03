# Session Efficiency Suggestions — Ranked by Recurrence

> Maintained by `.github/skills/session-close/SKILL.md` Step 4b. `Count` = number of sessions where this exact root cause recurred. Sorted by `Count` descending. Do not hand-edit `Count`; the skill
> owns it.

| Count | Slug | Suggestion | Category | First seen | Last seen |
|---|---|---|---|---|---|
| 24 | update-context-for-new-files | Update CONTEXT.md before commit whenever a session adds a new persistent repo file. | protocol-compliance | 2026-09-27 | 2026-10-02 |
| 23 | avoid-mid-session-rereads | Reuse already-loaded file context instead of re-reading the same file mid-session unless it changed. | token-efficiency | 2026-09-27 | 2026-10-03 |
| 21 | state-plan-before-editing | State the one-sentence plan before the first edit, even when the next task seems obvious from story order. | protocol-compliance | 2026-09-30 | 2026-10-03 |
| 21 | wait-for-explicit-go-ahead-before-editing | Wait for explicit reply after stating the plan, before creating/committing when approval required. | protocol-compliance | 2026-09-27 | 2026-10-03 |
| 19 | re-read-context-on-resumed-task-segments | On each resumed autopilot segment, re-open CONTEXT.md and state `CONTEXT.md ✓` before the next task. | protocol-compliance | 2026-10-02 | 2026-10-03 |
| 18 | confirm-target-files-before-starting | When destination files aren't named, confirm which files change before creating new modules/tests. | protocol-compliance | 2026-09-29 | 2026-10-02 |
| 10 | prefer-scoped-file-reads-over-full-cat-dumps | Prefer `view_range`/`sed -n`/`grep`/summaries over full `cat` dumps once target section is known. | token-efficiency | 2026-09-29 | 2026-10-02 |
| 10 | avoid-broad-filesystem-finds | Use repo-local `glob`/known paths instead of broad `find` probes for skill docs or session transcripts. | token-efficiency | 2026-09-27 | 2026-09-30 |
| 8 | state-context-md-checkmark-explicitly | State `CONTEXT.md ✓` verbatim in the first response, not just read the file silently before coding. | protocol-compliance | 2026-09-28 | 2026-10-02 |
| 5 | confirm-commit-sha-after-commit | After each commit, surface the resulting SHA in the user-facing summary instead of relying on git log output alone. | commit-hygiene | 2026-09-29 | 2026-10-02 |
| 5 | write-and-run-tests-before-commit | Add happy-path/edge-case tests for new public fns, run green before commit; missing harness isn't a stop. | protocol-compliance | 2026-09-29 | 2026-10-02 |
| 2 | context-md-not-read-on-query-sessions | Read and acknowledge CONTEXT.md at session start even for pure Q&A sessions with no code touched. | protocol-compliance | 2026-09-30 | 2026-09-30 |
| 1 | amend-local-only-commits-for-sha-backfill | For an unpushed commit followed by a SHA-backfill doc edit, use `git commit --amend` to fold it in. | commit-hygiene | 2026-10-02 | 2026-10-02 |
| 1 | minimize-context-in-subagent-delegation-prompts | When delegating to a self-extracting subagent, give a terse pointer, not a full summary. | token-efficiency | 2026-10-02 | 2026-10-02 |
| 1 | avoid-git-reset-hard-for-revert | Use `git revert` (new commit) not `git reset --hard`, which discards uncommitted changes too. | commit-hygiene | 2026-09-29 | 2026-09-29 |
| 1 | verify-commit-landed-after-precommit-stash | If pre-commit stashes unstaged files, re-check `git log -1` — a stash cycle can silently no-op it. | commit-hygiene | 2026-09-29 | 2026-09-29 |
| 1 | avoid-conflicting-parallel-file-ops | Do not run a destructive remove and a create for the same path in one parallel batch; sequence them. | token-efficiency | 2026-09-28 | 2026-09-28 |
