# Csv io lib migration — prompt

> Consolidate raw CSV I/O (reading/writing plain CSV structures — distinct from `report_render`'s formatted-report output) duplicated across `github_copilot` into `src/lib/csv_io/`, defining its
> `Protocol` here (deferred by `functional-code-taxonomy` FCT-2).

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/plan/functional-code-taxonomy/` FCT-1 and FCT-3 (the `report_render`-vs-`csv_io` boundary statement) are checked done before starting CIM-1 — this story must not blur the
line FCT-3 draws between raw CSV I/O and formatted report rendering.

## Why this story exists

`functional-code-taxonomy` named `csv_io` as a distinct module from `report_render` specifically to separate "read/write a CSV structure" (mechanical, format-agnostic) from "render a formatted report"
(shape-specific, Strategy-based). Both were named in the same audit of ad hoc CSV handling across `github_copilot`, but only `report_render` got a `Protocol` in FCT-2. This story builds `csv_io`'s
`Protocol` and implementer, reusing the audit's file list where the duplication is genuinely raw I/O (e.g. "read this CSV into dicts", "write these dicts to a CSV with this header") rather than shaped
report output.

## Scope guard

**In scope:** `src/lib/csv_io/protocols.py` (new `Protocol`) + `src/lib/csv_io/` concrete reader/writer implementer for plain CSV structures; tests; doc/`CONTEXT.md` pointers.

**Out of scope:** any formatted/shaped report output (that's `report_render`'s job — re-read FCT-3's boundary statement before drawing this story's own file list); any change under
`/Users/abhadra/github_copilot`.

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — epic architecture diagram and constraints.
- `docs/plan/functional-code-taxonomy/prompt.md` and `stories.md` (FCT-3's `report_render`/`csv_io`/`query-catalog` boundary table) — read before drawing this story's own scope line.
- `docs/plan/src-lib-migration/report-render-lib-migration/stories.md` — the sibling module this story must stay distinct from.
- `PYTHON_DESIGN.md` — DIP/ISP trigger sections.

## Task overview

- **CIM-1** — `src/lib/csv_io/protocols.py`: new `CsvReaderProtocol`/`CsvWriterProtocol` (split per ISP — a reader and a writer are separate concerns, not one interface with unused methods on either
  side).
- **CIM-2** — `src/lib/csv_io/csv_file.py`: concrete reader/writer implementer(s).
- **CIM-3** — Tests + `Protocol` conformance pairs.
- **CIM-4** — Doc/`CONTEXT.md` pointers.

## Definition of done

- `src/lib/csv_io/protocols.py` defines separate reader/writer `Protocol`s (ISP), each `@runtime_checkable`.
- `src/lib/csv_io/csv_file.py` implements both, verified via `isinstance`.
- Tests pass using `tmp_path` fixtures only, no real project directories touched.
- `CONTEXT.md` gains one new line.

## Perspectives not covered

- This story does not handle non-CSV tabular formats (e.g. Parquet, Excel) — scoped to CSV only, per the proven duplication; a broader tabular-I/O abstraction is a future story's problem if a real
  second format appears.
