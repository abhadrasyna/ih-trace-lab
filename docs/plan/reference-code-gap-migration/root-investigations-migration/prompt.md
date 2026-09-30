# root investigations migration — prompt

> Port root `github_copilot/investigations/` (player/session checks, Jira/search extraction, DRM-flow reporting, JWS signing — a grab-bag of small unrelated utilities) into
> `investigations/legacy-adhoc/` — Tier 2.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Root `/Users/abhadra/github_copilot/investigations/` (10 files) has no migration plan anywhere. Epic `spec.md` §5 audited it: 1 file (`get_final_answer.py`) is a `report_render` lib candidate; 9 stay
local (player/session checks, Jira extraction — `extract_jira.py`/`extract_jira2.py` duplicate each other and should be reconciled to one during the port, not both carried forward — search extraction,
DRM-flow reporting, JWS signing).

**Target-folder decision (epic GAP-1):** these 10 scripts share no single campaign narrative — they are disconnected, pre-taxonomy ad hoc checks, not one recurring relationship. Rather than invent a
per-script campaign slug each, they land together as one **bounded-case** folder, `investigations/legacy-adhoc/`, documented as a grab-bag with this reasoning stated in its own case doc — not silently
treated as a campaign per PT-2 Rule B.

**New-module decisions affecting 2 of these 10 files (epic GAP-1):** `generate_drm_flow_report.py` and `sign_jws_json.py` each share a real second consumer elsewhere (`mpd`/DASH parsing with
`vod-playback-timing-probe`; JWS signing with `smarttv-mtntv`) — both were promoted to future `src/lib/*` modules (`mpd`, `crypto_signing`). Those 2 files are **blocked** on those modules existing;
the other 8 are not.

## Scope guard

**In bounds:** `investigations/legacy-adhoc/` for 8 of the 10 files now; `generate_drm_flow_report.py` and `sign_jws_json.py` wait for `src/lib/mpd/`/`src/lib/crypto_signing/` in a later task.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/investigations` (read-only, never edited); `src/lib/*` internals;
`vod-playback-timing-probe-tool-migration`/`smarttv-mtntv-tool-migration` (this story does not build `mpd`/`crypto_signing` itself — only consumes them once `src-lib-migration` builds them).

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §5 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (target-folder reasoning, `mpd`/`crypto_signing` promotion).
- `docs/plan/project-taxonomy/structure.md` — the `investigations/<slug>/` (bounded-case) skeleton.
- `docs/plan/src-lib-migration/README.md` — `report_render` module status.

## Task overview

- **RIN-1** — Audit root `investigations/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §5, and reconcile `extract_jira.py`/`extract_jira2.py` into one
  target.
- Further tasks (skeleton port for the 8 unblocked files, then the 2 blocked files once `mpd`/`crypto_signing` land, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`investigations/legacy-adhoc/` exists with a case doc explaining its grab-bag nature; 8 of 10 scripts ported and tested (with `get_final_answer.py` importing `src/lib/report_render`, and
`extract_jira.py`/`extract_jira2.py` reconciled to one script); `generate_drm_flow_report.py` and `sign_jws_json.py` land in a follow-up task once their blocking modules exist. No file under
`/Users/abhadra/github_copilot` was touched.
