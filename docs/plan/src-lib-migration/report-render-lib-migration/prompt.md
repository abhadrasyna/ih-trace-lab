# Report render lib migration — prompt

> Port the 8+ duplicated CSV/report writers found across `github_copilot` into a single Strategy-based `src/lib/report_render/` implementing `functional-code-taxonomy` FCT-2's `Protocol`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/plan/functional-code-taxonomy/` FCT-1 and FCT-2 are checked done before starting RRM-2 — FCT-2 defines `src/lib/report_render/protocols.py`'s exact shape.

## Why this story exists

`functional-code-taxonomy`'s audit found CSV/report writing duplicated ad hoc across at least eight files in five projects (`ctap-smvod-session-report`, `aws-access-cli`, `applauseInvestigation`,
`mtn-zm-session-device-investigation`, `vod-playback-timing-probe`), with no shared writer anywhere — a textbook OCP violation (every new report format is a new copy-pasted `to_csv`/print-loop rather
than a new Strategy implementer). FCT-2 already scaffolded the `Protocol`; this story provides the concrete Strategy implementer(s) so a real consumer can use it instead of writing copy nine.

## Scope guard

**In scope:** `src/lib/report_render/` concrete writer(s) implementing FCT-2's `Protocol`, one Strategy implementer per report *shape* the audit found (not per-project — if two projects' writers are
shape-identical, one implementer covers both); tests; doc/`CONTEXT.md` pointers.

**Out of scope:** any project-specific report schema/column set (those stay local to a future consumer); any change under `/Users/abhadra/github_copilot`; the `Protocol` definition itself (already
FCT-2's, not re-litigated here).

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — epic architecture diagram and constraints.
- `docs/plan/functional-code-taxonomy/stories.md` (FCT-2 spec) and the landed `src/lib/report_render/protocols.py` — the exact interface this story implements against.
- `PYTHON_DESIGN.md` — Strategy pattern section; cite the OCP trigger this story resolves.

## Task overview

- **RRM-1** — Re-confirm the 8+ file audit list against current `github_copilot` state (read-only); group by report *shape*, not by project.
- **RRM-2** — `src/lib/report_render/writers.py`: Strategy implementer(s) per shape, satisfying FCT-2's `Protocol`.
- **RRM-3** — Tests + `Protocol` conformance pair.
- **RRM-4** — Doc/`CONTEXT.md` pointers.

## Definition of done

- Every cited original from the FCT-1 audit has a corresponding shape covered by a concrete implementer here, or an explicit note stating why it's excluded.
- `src/lib/report_render/writers.py` implements FCT-2's `Protocol`, verified via `isinstance`.
- Tests pass with no network/real filesystem side effects beyond a temp directory.
- `CONTEXT.md` gains one new line.

## Perspectives not covered

- This story does not migrate any existing consumer's call sites (no consumer exists yet in `ih-trace-lab`) — it produces the library only, per this epic's own scope decision.
