---
name: commit
description: Execute the full commit workflow (diff review, run tests, format the commit message, stage and commit, confirm the SHA). Use when the user asks to commit changes, or after any approved change that this project's protocol requires closing out with a commit.
---

# Commit Executor

Execute the full commit workflow. A written-out commit message is not a commit — this skill runs the git commands and confirms the SHA. The phase is not closed until the SHA appears.

---

## Step 1 — Review the diff

```bash
git -C /path/to/repo diff HEAD
```

Scan for anything a fresh pair of eyes would flag: missing type hints, leftover debug prints, an unrelated file swept in. If a `code-reviewer` agent is configured for this project (Tier 2), invoke it
before proceeding instead of relying on this scan alone.

---

## Step 2 — Run the test suite

Run whatever this project's test command is (e.g. `pytest --tb=no -q`, `npm test`, `go test ./...`) — record it in `CONTEXT.md` once tests exist so this step never has to guess. All tests must pass.
If any fail, do not proceed — fix failures first. If this project has no tests yet, this step is a legitimate skip, not a violation.

---

## Step 3 — Construct the commit message

Use this format exactly:

```
<type>(<scope>): <what changed, imperative mood, ≤60 chars>

Why: <one sentence — reason or problem solved, not a restatement of what changed>
What:
- <file path relative to repo root>: <one-line description>
- <file path relative to repo root>: <one-line description>
```

**Types:** `feat` / `fix` / `refactor` / `test` / `chore` / `docs` **Scope:** the module/folder most affected by the change.

Rules:
- Subject line ≤ 60 chars, imperative mood, no trailing period.
- `Why:` explains the reason, never just restates `What:`.
- One `What:` bullet per file changed.
- Never bundle unrelated changes into one commit.

---

## Step 4 — Stage and commit

```bash
git -C /path/to/repo add <file1> <file2> ...
git -C /path/to/repo commit -m "$(cat <<'EOF'
<paste message here>
EOF
)"
```

Stage only the files for this change — never `git add -A`/`git add .` blindly. If a `pre-commit` config exists and you want to run it by hand first, scope it: `pre-commit run --files $(git diff
--cached --name-only)`, never `--all-files` (that reformats the whole tree into your diff).

---

## Step 5 — Confirm the SHA (mandatory)

```bash
git -C /path/to/repo log --oneline -1
```

The SHA must appear in output. This is proof of completion. If this step is skipped, the phase is not closed.

---

## Type reference

| Type | When |
|---|---|
| `feat` | New capability added |
| `fix` | Bug or incorrect behaviour corrected |
| `refactor` | Restructuring with no behaviour change |
| `test` | Test added or updated |
| `chore` | Tooling, config, deps, scripts |
| `docs` | Documentation only |

## Example

```
feat(scratch): add daily-snapshot POC script

Why: need to prove the fetch/parse shape before writing the real module
What:
- scratch/2026-09-26_daily_snapshot_probe.py: quick end-to-end POC
```
