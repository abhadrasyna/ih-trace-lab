# shaka-6001-sa-error-analysis migration — prompt

> Port `shaka-6001-sa-error-analysis` (daily/session Shaka playback error queries for South Africa) into `investigations/shaka-6001-sa/` — Tier 1, cheap, no new module.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/shaka-6001-sa-error-analysis` (6 files) has no migration plan anywhere. Epic `spec.md` §7 audited it: `athena_runner.py` and `aws_sso.py` are `athena`/`auth` lib
candidates; `user_agent_parser.py`, `query_daily_shaka_errors.py`, `query_session_shaka_errors.py` stay local business logic. `user_agent_parser.py`'s overlap with
`mtn-zm-session-device-investigation/scripts/athena_runner/tenants.py` is only at the tenant-configuration boundary (per epic `README.md`'s new-module decisions) — accepted as local duplication, not
promoted to a `device_identity` module, unless a third project needs the same UA parsing.

## Scope guard

**In bounds:** `investigations/shaka-6001-sa/` (new campaign slug — not yet worked-example'd in `project-taxonomy/structure.md`) — auditing/confirming `spec.md` §7's classification, then (later)
skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/shaka-6001-sa-error-analysis` (read-only, never edited); `src/lib/{athena,auth}` internals; any other sub-story.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §7 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (Tier 1; device/UA-identity accept-local decision).
- `docs/plan/project-taxonomy/structure.md` — `investigations/<slug>/` skeleton.
- `docs/plan/src-lib-migration/README.md` — `athena`/`auth` module status.

## Task overview

- **SHK-1** — Audit `shaka-6001-sa-error-analysis/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §7.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`investigations/shaka-6001-sa/` exists, fully tested, importing `src/lib/{athena,auth}` for execution/SSO concerns; user-agent parsing and daily/session Shaka-error query logic stay local. No file
under `/Users/abhadra/github_copilot` was touched.
