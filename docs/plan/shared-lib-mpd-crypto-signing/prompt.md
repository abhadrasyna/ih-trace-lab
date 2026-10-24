# Shared libs `mpd` and `crypto_signing` — prompt

> Build the two shared modules `src/lib/mpd/` and `src/lib/crypto_signing/` that `reference-code-gap-migration` promoted but no story owns.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`reference-code-gap-migration` (GAP-1, 2026-09-30) applied the "two or more real consumers" test from `docs/guides/functional-code-taxonomy.md` and promoted two modules: `src/lib/mpd/` (MPEG-DASH
parsing) and `src/lib/crypto_signing/` (JWS/JSON signing). It recorded the decision but did not build them, and `src-lib-migration` (the intended owner) is archived without ever adding them.

Two stories are blocked until these exist: `vod-playback-timing-probe-tool-migration` (needs `mpd`) and `smarttv-mtntv-tool-migration` (needs `crypto_signing`). Two files in
`root-investigations-migration` also depend on them.

## Scope guard

In bounds: new packages `src/lib/mpd/` and `src/lib/crypto_signing/`, their tests, `docs/guides/functional-code-taxonomy.md`, the code registry and `CONTEXT.md`.

Out of bounds: migrating any consumer (the two blocked stories and `root-investigations-migration` do that), and the `github_copilot` originals, which are read-only references. Adds new library code
only; no existing runtime behaviour changes.

## Session-start load hints

- `docs/guides/functional-code-taxonomy.md` (shared-vs-specific test, Protocol rules) and `docs/refactor/` (wrap third-party exceptions at the module boundary).
- `docs/plan/reference-code-gap-migration/README.md` (decision table and consumer list) and `spec.md` (file-by-file audit evidence).
- Existing package for shape reference: `src/lib/har/` and `src/lib/charts/` (`errors.py` boundary pattern).
- Originals, read-only: `/Users/abhadra/github_copilot/vod-playback-timing-probe/scripts/playback_probe/mpd_parser.py`,
  `/Users/abhadra/github_copilot/investigations/scripts/generate_drm_flow_report.py`, `/Users/abhadra/github_copilot/smarttv-mtntv/scripts/signedJson.py`,
  `/Users/abhadra/github_copilot/investigations/scripts/sign_jws_json.py`.

## Task overview

- **SLM-1** — Audit the four originals and record the shared API for both modules.
- **SLM-2** — Build `src/lib/mpd/`.
- **SLM-3** — Build `src/lib/crypto_signing/`.
- **SLM-4** — Update the taxonomy guide, code registry and `CONTEXT.md`; unblock the dependent stories.

## Definition of done

Both packages exist with typed public functions, a boundary error type and offline tests; docs and registry list them; the three dependent stories no longer name them as missing. Mirrors `tasks.md`
"Story done when".

## Perspectives not covered

- Signing key handling: the originals' key sourcing and any secrets are only audited in SLM-1; no key-management or rotation design is in scope.
- Migrating the consumers is left to their own stories, so the shared API is only proven against fixtures here.
