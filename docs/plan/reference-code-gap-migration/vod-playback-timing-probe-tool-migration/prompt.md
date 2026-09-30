# vod-playback-timing-probe migration — prompt

> Port `vod-playback-timing-probe` (CTAP/VOD playback flow replay, HAR/cURL flow extraction, probe-vs-HAR timing comparison) into `src/tools/vod-playback-timing-probe/` — Tier 3, **blocked on
> `src/lib/mpd/` existing**.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/vod-playback-timing-probe` (65 files: ~35 implementation + tests) has no migration plan anywhere — cited elsewhere only as a `har`/`curl_to_python` duplication source.
Epic `spec.md` §1 audited it: approximately 12 files fit existing `har`/`auth`/`curl_to_python`/`report_render`/`paths`; approximately 23 remain playback-specific (flow orchestration, CTAP client,
license/manifest/segment steps, session simulation, MPD/DASH parsing, timing computation).

**New-module decision (epic GAP-1):** `mpd_parser.py` (MPEG-DASH MPD parsing) has a real second consumer — root `investigations/scripts/generate_drm_flow_report.py` — and was **promoted** to
`src/lib/mpd/`. This story is blocked on that module existing (built by `src-lib-migration`, not by this story). A playback-session/timing correlator module was considered and **not** promoted — this
project is its only true consumer (the flagged overlap with `mtn-network-traffic/scripts/curl_timer/curl_timing.py` is superficial: cURL network timing vs. playback-flow timing correlation are
different mechanisms).

## Scope guard

**In bounds:** `src/tools/vod-playback-timing-probe/` — auditing/confirming `spec.md` §1's classification now; actual port waits for `src/lib/mpd/` to exist.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/vod-playback-timing-probe` (read-only, never edited); building `src/lib/mpd/` itself (that is `src-lib-migration`'s task, once picked
up, per the coordination note in epic `README.md`); `src/lib/{har,auth,curl_to_python,report_render}` internals; any other sub-story.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §1 — this project's full per-file audit table (the largest of the 10).
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (`mpd` promotion, playback-timing accept-local decision).
- `docs/plan/project-taxonomy/structure.md` — the `src/tools/<slug>/` skeleton; note the flagged, unresolved tool-vs-experiment tension for this project (not this story's job to resolve).
- `docs/plan/src-lib-migration/README.md` — `har`/`auth`/`curl_to_python`/`report_render` module status, and whether `mpd` has been added yet.

## Task overview

- **VTP-1** — Audit `vod-playback-timing-probe/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §1 (audit-only — do not attempt a port; `src/lib/mpd/` does
  not exist yet).
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written — blocked until `src/lib/mpd/` lands.

## Definition of done

`spec.md` §1's classification is confirmed/refined for all ~35 implementation files, with the `mpd`-dependent subset (`mpd_parser.py` and its direct callers) explicitly flagged as blocked. No actual
port happens in this task. No file under `/Users/abhadra/github_copilot` was touched.
