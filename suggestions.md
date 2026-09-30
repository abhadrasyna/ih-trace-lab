# Session Efficiency Suggestions — Ranked by Recurrence

> Maintained by `.github/skills/session-close/SKILL.md` Step 4b. `Count` = number of sessions where this exact root cause recurred. Sorted by `Count` descending. Do not hand-edit `Count`; the skill
> owns it.

| Count | Slug | Suggestion | Category | First seen | Last seen |
|---|---|---|---|---|---|
| 10 | avoid-broad-filesystem-finds | Use repo-local `glob`/known paths instead of broad `find` probes for skill docs or session transcripts. | token-efficiency | 2026-09-27 | 2026-09-30 |
| 10 | avoid-mid-session-rereads | Reuse already-loaded file context instead of re-reading the same file mid-session unless it changed. | token-efficiency | 2026-09-27 | 2026-09-30 |
| 8 | wait-for-explicit-go-ahead-before-editing | After stating the plan, wait for explicit reply before creating/committing when approval is needed. | protocol-compliance | 2026-09-27 | 2026-09-29 |
| 5 | update-context-for-new-files | Update CONTEXT.md before commit whenever a session adds a new persistent repo file. | protocol-compliance | 2026-09-27 | 2026-09-30 |
| 4 | state-context-md-checkmark-explicitly | State `CONTEXT.md ✓` verbatim in the first response, not just read the file silently before coding. | protocol-compliance | 2026-09-28 | 2026-09-30 |
| 4 | prefer-scoped-file-reads-over-full-cat-dumps | Prefer `view_range`/`sed -n`/`grep`/summaries over full `cat` dumps once target section is known. | token-efficiency | 2026-09-29 | 2026-09-30 |
| 2 | context-md-not-read-on-query-sessions | Read and acknowledge CONTEXT.md at session start even for pure Q&A sessions with no code touched. | protocol-compliance | 2026-09-30 | 2026-09-30 |
| 2 | write-and-run-tests-before-commit | Add happy-path/edge-case tests for new public fns, run green before commit; missing harness isn't a stop. | protocol-compliance | 2026-09-29 | 2026-09-30 |
| 1 | state-plan-before-editing | State the one-sentence plan before the first edit, even when an evaluation request turns into "apply the edits." | protocol-compliance | 2026-09-30 | 2026-09-30 |
| 1 | avoid-conflicting-parallel-file-ops | Do not run a destructive remove and a create for the same path in one parallel batch; sequence them. | token-efficiency | 2026-09-28 | 2026-09-28 |
| 1 | confirm-target-files-before-starting | When source folders but not destination files are named, stop to confirm scope and which files change. | protocol-compliance | 2026-09-29 | 2026-09-29 |
| 1 | confirm-commit-sha-after-commit | After each commit, surface the resulting SHA in the user-facing summary instead of relying on git log output alone. | commit-hygiene | 2026-09-29 | 2026-09-29 |
| 1 | verify-commit-landed-after-precommit-stash | If pre-commit stashes unstaged files, re-check `git log -1` — a stash cycle can silently no-op it. | commit-hygiene | 2026-09-29 | 2026-09-29 |
| 1 | avoid-git-reset-hard-for-revert | Use `git revert` (new commit) not `git reset --hard`, which discards uncommitted changes too. | commit-hygiene | 2026-09-29 | 2026-09-29 |
