# Har lib migration — prompt

> Port the 4 duplicated HAR-entry loaders found across `github_copilot` into a single `src/lib/har/` implementing `functional-code-taxonomy` FCT-2's `Protocol`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/archive/functional-code-taxonomy/` FCT-1 and FCT-2 are checked done before starting HLM-2 — FCT-2 defines `src/lib/har/protocols.py`'s exact shape, seeded from
`vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()`.

## Why this story exists

`functional-code-taxonomy`'s function-body-level audit found the same ~5-line "load HAR `log.entries`" loader reimplemented four times: `applauseInvestigation/scripts/ analyze_har.py::iter_entries()`,
`vod-playback-timing-probe/scripts/ extract_content_ids_from_har.py::_load_entries()`, `vod-playback-timing-probe/scripts/summarize_har_playbacks.py::_load_entries()` (twice within the *same*
project), and `vod-asset-ingestion-mapping/scripts/lib/har_parser.py:: load_json_entries()` (the one project that isolated it into its own file — used as FCT-2's seed). This is a textbook
SRP/duplication violation: a pure domain-mechanism function with no business being copy-pasted per project.

## Locked-in decisions (requester-approved 2026-10-02)

- **Loader input type:** accept both a file path and an open file handle (`str | Path | IO`), not path-only.
- **Malformed-HAR validation scope:** broad — reject non-dict `log`, non-list `entries`, and invalid JSON, not just "missing `log.entries`."
- **Four originals, canonical source — RESOLVED (requester-approved 2026-10-02):** HLM-1's re-audit found real divergence, not just copy-paste cosmetics. `load_json_entries()` bundles two concerns:
  loading `log.entries` (shared across all four) and JSON-mimetype/URL filtering + response-body parsing (unique to `vod-asset-ingestion-mapping`, and not representable by the already-landed
  `HarEntry` dataclass, which has no response-content field). Resolution: the shared loader covers the "load `log.entries`" mechanism identically for all four originals; `load_json_entries()`'s
  filter/parse behavior is explicitly excluded as project-specific business logic per this project's own shared-vs-specific test, not a gap in HLM-2. See `stories.md`'s HLM-1 section for the full
  citation. No sign-off blocks HLM-2 — proceed.

## Scope guard

**In scope:** `src/lib/har/` concrete loader implementing FCT-2's `Protocol`; tests; doc/ `CONTEXT.md` pointers.

**Out of scope:** any HAR-entry *filtering*/business-rule logic specific to one investigation (e.g. content-ID extraction rules) — those stay local to a future consumer; any change under
`/Users/abhadra/github_copilot`; the `Protocol` definition itself (FCT-2's).

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — epic architecture diagram and constraints.
- `docs/archive/functional-code-taxonomy/stories.md` (FCT-2 spec) and the landed `src/lib/har/protocols.py` — the exact interface this story implements against.
- `PYTHON_DESIGN.md` — SRP trigger section.

## Task overview

- **HLM-1** — Re-confirm the 4-copy audit list against current `github_copilot` state (read-only).
- **HLM-2** — `src/lib/har/loader.py`: concrete loader satisfying FCT-2's `Protocol`.
- **HLM-3** — Tests + `Protocol` conformance pair.
- **HLM-4** — Doc/`CONTEXT.md` pointers.

## Definition of done

- Every cited original from the FCT-1 audit is covered by `src/lib/har/loader.py`'s behavior, or an explicit note states why it diverges. **Resolved 2026-10-02:** three originals (`analyze_har.py`,
  `extract_content_ids_from_har.py`, `summarize_har_playbacks.py`) are fully covered by the shared `load_entries()` mechanism; `vod-asset-ingestion-mapping/.../load_json_entries()` is covered only for
  its `log.entries`-loading sub-behavior — its JSON-mimetype/URL filtering and response-body parsing is explicitly excluded as project-specific logic (see `stories.md` HLM-1).
- `src/lib/har/loader.py` implements FCT-2's `Protocol`, verified via `isinstance`.
- Tests pass with no network calls (fixture HAR files only).
- `CONTEXT.md` gains one new line.

## Perspectives not covered

- This story does not migrate any existing consumer's call sites (no consumer exists yet in `ih-trace-lab`) — it produces the library only.
