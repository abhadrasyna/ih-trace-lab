# Curl to python lib migration — prompt

> Consolidate curl→Python conversion helpers duplicated across `github_copilot` into `src/lib/curl_to_python/`, defining its `Protocol` here (deferred by `functional-code-taxonomy` FCT-2).

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/plan/functional-code-taxonomy/` FCT-1 is checked done before starting CPM-1 — re-derive this module's originals from that story's audit rather than re-auditing
`github_copilot` from scratch.

## Why this story exists

`functional-code-taxonomy` named `curl_to_python` as one of the six `src/lib/*` modules (curl-command-to-Python-requests-call conversion, used when turning a captured browser/HAR curl command into a
repeatable investigation script) but did not scope a `Protocol` for it — lowest proven duplication of the six at FCT-1's audit time. **Confirmed real consumer (2026-10-01, in the
`pre-implementation-design-review` follow-up conversation):** this module's actual invocation shape is manual/ad hoc, not pipeline-automated — during a HAR-driven timing/latency investigation (e.g.
`vod-playback-timing-probe`, `applauseInvestigation`), an analyst identifies a specific request in a HAR file, copies that request's curl command (as exported by browser devtools), and invokes this
converter to get a repeatable Python script for re-running/measuring that single request's timing. This is not a speculative build-ahead-of-a-trigger module; the trigger is this HAR-investigation
workflow, confirmed as real rather than hypothetical.

## Scope guard

**In scope:** `src/lib/curl_to_python/protocols.py` (new `Protocol`) + `src/lib/curl_to_python/` concrete converter implementer; tests; doc/`CONTEXT.md` pointers.

**Out of scope:** any investigation-specific request-shaping logic (headers/auth tokens specific to one tenant/service) — stays local to a future consumer; any change under
`/Users/abhadra/github_copilot`.

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — epic architecture diagram and constraints.
- `docs/plan/functional-code-taxonomy/prompt.md`/`stories.md` — re-read for any `curl_to_python`-relevant audit citations before CPM-1.
- `PYTHON_DESIGN.md` — SRP/Factory Method trigger sections (parsing a curl command into structured parts is a natural Factory Method: one function owns "which Python call shape results from this curl
  command," rather than branching inline at each call site).

## Task overview

- **CPM-1** — Confirm/derive the originals this module replaces from the FCT-1 audit, and record the confirmed consumer scenario (HAR-driven timing/latency investigation: analyst copies a single
  request's curl command identified via HAR inspection, converts it for repeatable re-testing) rather than treating this as a speculative build-ahead-of-a-trigger module.
- **CPM-2** — `src/lib/curl_to_python/protocols.py`: new `CurlConverterProtocol`.
- **CPM-3** — `src/lib/curl_to_python/converter.py`: concrete implementer.
- **CPM-4** — Tests + `Protocol` conformance pair.
- **CPM-5** — Doc/`CONTEXT.md` pointers.

## Definition of done

- CPM-1's finding (cited originals, or an explicit "none found" note) is recorded before any code is written.
- `src/lib/curl_to_python/protocols.py` defines a `Protocol`-only interface, `@runtime_checkable`.
- `src/lib/curl_to_python/converter.py` implements it, verified via `isinstance`.
- Tests pass with no network calls (parses curl command strings only, does not execute them).
- `CONTEXT.md` gains one new line.

## Perspectives not covered

- This story does not execute the converted Python code, only produces it as text/AST — actual execution is a future consumer's responsibility, keeping this module free of side effects and easy to
  test.
