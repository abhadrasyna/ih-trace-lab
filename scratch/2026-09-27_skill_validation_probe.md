# Skill validation probe — 2026-09-27

Purpose: exercise the `commit` skill and the `session-close` skill end-to-end
to confirm both work as documented in `.github/skills/`.

- `commit` skill: this file's creation + commit is the test artifact.
- `session-close` skill: run separately against this session's own
  `events.jsonl` transcript (fresh subagent, per skill instructions).
