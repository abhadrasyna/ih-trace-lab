# Csv io lib migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: CIM-1, CIM-2, CIM-3, CIM-4.**

- [ ] **CIM-1** — `src/lib/csv_io/protocols.py`: split `CsvReaderProtocol`/`CsvWriterProtocol` (ISP) | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green |
  SHA: <—>
- [ ] **CIM-2** — `src/lib/csv_io/csv_file.py`: concrete reader/writer implementer(s) | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **CIM-3** — Tests + `Protocol` conformance pairs | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **CIM-4** — Doc/`CONTEXT.md` pointers | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **CIM-1** — `src/lib/csv_io/protocols.py` defines `CsvReaderProtocol` and `CsvWriterProtocol` as separate `Protocol`s (no shared interface forcing unused methods on either side),
  `@runtime_checkable`.
- **CIM-2** — `src/lib/csv_io/csv_file.py` implements both protocols with concrete classes.
- **CIM-3** — `pytest` passes using `tmp_path` fixtures only; `Protocol` conformance confirmed via `isinstance` for both interfaces.
- **CIM-4** — `CONTEXT.md` gains one new "What Exists" line; epic `README.md` status table updated to ✅ Done with closing SHA.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
