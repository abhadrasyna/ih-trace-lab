# smarttv-mtntv migration — prompt

> Port `smarttv-mtntv` (signs JSON payloads for SmartTV/MTN TV requests) into `src/tools/smarttv-mtntv/` — Tier 3, **blocked on `src/lib/crypto_signing/` existing**.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/smarttv-mtntv` (1 file, `scripts/signedJson.py`, 50 LOC) has no migration plan anywhere. Epic `spec.md` §10 audited it: a local JWS/JSON-signing script.

**New-module decision (epic GAP-1):** this script shares a real second consumer — root `investigations/scripts/sign_jws_json.py` — both doing the same JWS-signing mechanism. Promoted to
`src/lib/crypto_signing/` despite the small combined size (2 files, ~124 LOC), because the FCT-1 test is about shared mechanism, not file count. This story is blocked on that module existing (built by
`src-lib-migration`, not by this story).

## Scope guard

**In bounds:** `src/tools/smarttv-mtntv/` — auditing/confirming `spec.md` §10's classification now; actual port waits for `src/lib/crypto_signing/` to exist.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/smarttv-mtntv` (read-only, never edited); building `src/lib/crypto_signing/` itself (that is `src-lib-migration`'s task, once picked
up, per the coordination note in epic `README.md`); `root-investigations-migration` (that story ports `sign_jws_json.py`, the other `crypto_signing` consumer — not this one).

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §10 — this project's one-file audit entry.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (`crypto_signing` promotion).
- `docs/plan/project-taxonomy/structure.md` — the `src/tools/<slug>/` skeleton.
- `docs/plan/src-lib-migration/README.md` — check whether `crypto_signing` has been added to that epic's module list yet.

## Task overview

- **SMT-1** — Audit `smarttv-mtntv/scripts/signedJson.py` and confirm its classification/blocking status (audit-only — do not attempt a port; `src/lib/crypto_signing/` does not exist yet).
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written — blocked until `src/lib/crypto_signing/` lands.

## Definition of done

`spec.md` §10's one-file classification is confirmed, with its shared mechanism with `sign_jws_json.py` (root `investigations/`) explicitly documented. No actual port happens in this task. No file
under `/Users/abhadra/github_copilot` was touched.
