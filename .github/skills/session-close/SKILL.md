---
name: session-close
description: Generate an end-of-session protocol-compliance and token-efficiency self-audit report from a session transcript. Use when the user asks for "session close", "close the session", or an "end of session report".
---

# Session Close Skill

> Invoke at the end of any work session to produce a protocol-compliance and token-efficiency report. Trigger phrases: "session close", "close the session", "end of session report". Goal: honest
> self-audit — a diagnostic, not a trophy. Steps skipped need accurate labels, not post-hoc rationalization. **Runs on a transcript, not "this conversation."** The invoking prompt supplies an absolute
> path to a session's `.jsonl` transcript. This skill never inherits the session it audits — invoke it as a fresh subagent so the audit's own cost stays a bounded extraction against a file, not a full
> context clone. If no transcript path was given, ask for one; do not guess.

---

## Step 1 — Build the session's action log from the transcript

Extract, don't reconstruct — read only what each check below needs, never the whole transcript. `T` = the transcript path.

```bash
# tool calls in invocation order: tool name + a short arg summary
jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") |
  "\(.name)\t\((.input.file_path // .input.qualified_name // .input.query //
  .input.pattern // .input.subagent_type // .input.skill //
  (.input.command|tostring))[0:120])"' "$T"

# latest commit (confirms Step 5c, gives the SHA for the report)
git -C <repo> log --oneline -5
```

From the tool-call list, derive: which files were read; which bash commands ran (test runner, `git commit`, `git add`); which skills were invoked (`commit`). This list is the sole source of truth for
Step 2 — do not fall back to inference about what "probably" happened.

---

## Step 2 — Score each protocol step

For every step below, mark one of:

- ✅ **FOLLOWED** — step was completed as specified
- ⚠️ **LEGITIMATE SKIP** — step genuinely did not apply (give one-line reason)
- ❌ **VIOLATION** — step applied but was skipped or shortcut (give one-line reason)

### Protocol checklist (Tier 0 — `AGENTS.md` Steps 1–5 only)

| # | Step | Status | Reason (if not FOLLOWED) |
|---|---|---|---|
| 1 | CONTEXT.md read at session start | | |
| 2 | Scope confirmed (files named, or asked if not) | | |
| 3 | Plan stated in one sentence + go-ahead received | | |
| 4 | Tests written (happy path + edge case per public fn) | | |
| 5a | CONTEXT.md updated if new files were added | | |
| 5b | Tests confirmed green before commit | | |
| 5c | Commit executed (not drafted) + SHA confirmed | | |

<!--
Add rows for Step 2b (council checkpoint), Step 3b (Antigravity routing), and any domain-specific AutoTrigger agents once the project actually adopts Tier 2. Not applicable at Tier 0 — do not score
them until they exist. -->

### Classification rules

**Mark LEGITIMATE SKIP when:**
- Session was a query or read-only task (steps 2–5 don't apply to any of it)

**Mark VIOLATION when:**
- Step 3 was skipped — implementation started immediately after CONTEXT.md read with no plan stated
- SHA was not confirmed after commit (`commit` skill Step 5 skipped)
- CONTEXT.md was not updated after new files or modules were added

---

## Step 3 — Token efficiency audit

### 3a — Avoidable re-reads

List any files that were read more than once this session, or read when their content was already present in context (e.g. CONTEXT.md re-read mid-session after Step 1).

```
Avoidable re-reads: N
  - CONTEXT.md re-read mid-session (already loaded at Step 1)
```

### 3b — Bash output discipline

Check any bulk reads that ran this session. Flag a full-file dump where a scoped grep/tail/aggregate would have done, or a full test suite run in verbose mode with no failure being debugged.

```
Output-discipline flags: N
  - cat full_log.txt instead of tail -20 or grep ERROR
```

---

## Step 4 — Improvement suggestions

Based only on violations and patterns actually observed this session, produce 0–4 suggestions. Do not generate generic advice if the session was clean.

```
[SUGGESTION] <category>: <one-sentence action>
  Why it matters: <one sentence on token or correctness impact>
  Next session trigger: <the exact situation where this applies>
```

Categories: `token-efficiency` | `protocol-compliance` | `commit-hygiene`

If the session was clean: state "No suggestions — session followed protocol." and stop.

---

## Step 4b — Rank into `suggestions.md` (repo root)

Every suggestion from Step 4 is a candidate row in `suggestions.md` at the repo root — a running, cross-session tally of which inefficiency patterns actually recur.

1. Read `suggestions.md` if it exists (create it with the header below if not).
2. For each Step 4 suggestion, decide whether it matches an existing row's `Slug` (same root cause, not just similar wording). If matched: increment `Count`, update `Last seen`. If not: append a new
   row (`Count = 1`, `First seen = Last seen = today`, a new kebab-case `Slug`).
3. Re-sort by `Count` descending, ties broken by most recent `Last seen`.
4. Write the file back. Never hand-edit `Count` outside this procedure.

**File format:**

```markdown
# Session Efficiency Suggestions — Ranked by Recurrence

> Maintained by `.github/skills/session-close/SKILL.md` Step 4b. `Count` =
> number of sessions where this exact root cause recurred. Sorted by
> `Count` descending. Do not hand-edit `Count`; the skill owns it.

| Count | Slug | Suggestion | Category | First seen | Last seen |
|---|---|---|---|---|---|
```

If Step 4 produced no suggestions (clean session), do not touch `suggestions.md` at all.

<!--
Escalation of a recurring Count>=5 slug into a formal debt-tracking doc is a Tier 1+ concern (needs a docs/plan/ or equivalent backlog to escalate into). At Tier 0, a slug crossing 5 is simply a
strong signal worth raising with the operator directly — no automated escalation path yet. -->

---

## Step 4c — Append a row to `session_audit.jsonl` (repo root)

Unlike `suggestions.md` (Step 4b), this row is written for every session-close run, including a clean one with zero Step 4 suggestions.

```bash
python3 -c "
import json, sys, datetime
row = {
    'session_id': sys.argv[1],
    'date': datetime.date.today().isoformat(),
    'avoidable_rereads': int(sys.argv[2]),
    'output_discipline_flags': int(sys.argv[3]),
    'suggestions_count': int(sys.argv[4]),
}
with open('session_audit.jsonl', 'a') as f:
    f.write(json.dumps(row) + '\n')
" "$SESSION_ID" "$AVOIDABLE_REREADS" "$OUTPUT_FLAGS" "$SUGGESTIONS_COUNT"
```

No external CLI dependency — a plain inline script, since Tier 0 has no `scripts/dev/` tooling yet.

---

## Step 5 — Produce the final report block

Output this compact block. One screen maximum.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION CLOSE — <YYYY-MM-DD> — <one-line task description>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROTOCOL COMPLIANCE
  Steps followed:    <count> / 7
  Legitimate skips:  <count> — <comma-separated step IDs>
  Violations:        <count> — <comma-separated step IDs>

  Violations detail:
    ❌ Step <ID> (<name>): <reason — one line>

TOKEN EFFICIENCY
  Avoidable re-reads:      <count>
  Output-discipline flags: <count>

SUGGESTIONS
  [SUGGESTION] <category>: <action>
    Why it matters: ...
    Next session trigger: ...
    suggestions.md: <new row | incremented "<slug>" to N>

COMMIT
  SHA: <hash — or "no commit this session">
  Tests at close: <N> passed, <N> failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If no violations and no token issues: output "Clean session." and omit empty sections.
