# mtn-network-traffic migration — prompt

> Port `mtn-network-traffic` (HTTP/cURL timing + network-path diagnostics: DNS, TLS, MTR, traceroute, WHOIS, JWT inspection, Markdown reporting) into `src/tools/mtn-network-traffic/` — Tier 2.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/mtn-network-traffic` (22 files: 13 implementation + 9 tests) has no migration plan anywhere — cited elsewhere only as the cURL-to-Python converter's duplication source.
Epic `spec.md` §3 audited it: approximately 6 implementation files fit existing `curl_to_python`/`report_render`/`auth`; approximately 7 remain network-diagnostic-specific (DNS/TLS/MTR/
traceroute/WHOIS probes).

**New-module decision (epic GAP-1):** a genuinely new "network diagnostics" module was considered and **not** promoted — this project is its only real consumer. Accepted as local duplication, revisit
only if a third project needs the same DNS/TLS/MTR/traceroute/WHOIS mechanisms.

## Scope guard

**In bounds:** `src/tools/mtn-network-traffic/` — auditing/confirming `spec.md` §3's classification, then (later) skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/mtn-network-traffic` (read-only, never edited); `src/lib/{curl_to_python,report_render,auth}` internals; any other sub-story.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §3 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (network-diagnostics accept-local decision).
- `docs/plan/project-taxonomy/structure.md` — the `src/tools/<slug>/` skeleton (this category has no `investigations/docs` — it is not a case).
- `docs/plan/src-lib-migration/README.md` — `curl_to_python`/`report_render`/`auth` module status.

## Task overview

- **MNT-1** — Audit `mtn-network-traffic/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §3.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`src/tools/mtn-network-traffic/` exists, fully tested, importing `src/lib/{curl_to_python,report_render,auth}` where applicable; DNS/TLS/MTR/traceroute/WHOIS probe logic and JWT inspection stay local.
No file under `/Users/abhadra/github_copilot` was touched.
