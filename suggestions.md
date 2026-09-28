# Session Efficiency Suggestions — Ranked by Recurrence

> Maintained by `.github/skills/session-close/SKILL.md` Step 4b. `Count` =
> number of sessions where this exact root cause recurred. Sorted by
> `Count` descending. Do not hand-edit `Count`; the skill owns it.

| Count | Slug | Suggestion | Category | First seen | Last seen |
| 8 | avoid-broad-filesystem-finds | Use repo-local `glob` or known paths instead of broad filesystem `find` probes when locating skill docs or session transcripts. | token-efficiency | 2026-09-27 | 2026-09-28 |
| 5 | avoid-mid-session-rereads | Reuse already-loaded file context instead of re-reading the same repo files mid-session unless the file changed. | token-efficiency | 2026-09-27 | 2026-09-28 |
| 3 | wait-for-explicit-go-ahead-before-editing | After stating the plan, wait for an explicit user reply before creating files or committing when the protocol requires approval. | protocol-compliance | 2026-09-27 | 2026-09-28 |
| 3 | state-context-md-checkmark-explicitly | State `CONTEXT.md ✓` verbatim in the first user-facing response, not just read the file silently before writing code. | protocol-compliance | 2026-09-28 | 2026-09-28 |
| 2 | update-context-for-new-files | Update `CONTEXT.md` before commit whenever a session adds a new persistent repo file. | protocol-compliance | 2026-09-27 | 2026-09-27 |
| 1 | avoid-conflicting-parallel-file-ops | Do not run a destructive remove and a create for the same path in one parallel batch; sequence them. | token-efficiency | 2026-09-28 | 2026-09-28 |
