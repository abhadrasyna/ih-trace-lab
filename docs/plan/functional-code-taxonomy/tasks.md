# Functional code taxonomy — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: FCT-1, FCT-2, FCT-3, FCT-4, FCT-5, FCT-6, FCT-7.**

- [ ] **FCT-1** — `docs/guides/functional-code-taxonomy.md`: six-module map + replaced-originals evidence + shared-vs-specific test | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review:
  human diff review | SHA: <—>
- [ ] **FCT-2** — `src/lib/{athena,report_render,har}/protocols.py`: `Protocol` skeletons + tests | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA:
  <—>
- [ ] **FCT-3** — same doc: migration/ownership table + query-catalog boundary | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **FCT-4** — `AGENTS.md` pointer line | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **FCT-5** — `CONTEXT.md` pointer line | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **FCT-6** — `scripts/dev/generate_code_registry.py` + doc section: cross-project registry + delegated duplicate-check | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human
  confirms tests green | SHA: <—>
- [ ] **FCT-7** — `src/lib/paths/protocols.py` + resolver: config-driven data/knowledge/investigations path AND filename resolution | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review:
  human confirms tests green | SHA: <—>

## Story done when

- **FCT-1** — `docs/guides/functional-code-taxonomy.md` names `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/`, each with a one-paragraph responsibility and at least one specific
  `github_copilot` file it is meant to replace (e.g. `athena` cites all four duplicated executors by path, `har` cites all four duplicated loader functions by path); the doc also states the "shared
  vs. specific" test in one place: logic operating on a domain mechanism (Athena, CSV/report I/O, HAR parsing) is a `src/lib/` candidate *by definition*, regardless of which project needs it first;
  only campaign/case-specific business rules stay local to a project's own `scripts/`.
- **FCT-2** — All three `protocols.py` files define `Protocol` classes only (`abc`/`typing.Protocol`, `@runtime_checkable` where instance checks are meaningful) with method signatures but no bodies
  beyond `...`; `pytest` confirms a minimal hand-written conforming class satisfies each `Protocol` via `isinstance`, and a non-conforming stub does not. `src/lib/har/protocols.py` is seeded from
  `vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()`'s shape (read-only reference, not copied verbatim).
- **FCT-3** — The guide doc has a table mapping each `docs/plan/project-taxonomy/` category to which `src/lib/*` modules it consumes, plus one explicit sentence: "`query-catalog` owns SQL text; this
  story owns the code that executes it."
- **FCT-4** — `AGENTS.md` gained one pointer line stating `docs/guides/functional-code-taxonomy.md` is where `PYTHON_DESIGN.md`'s triggers are applied concretely.
- **FCT-5** — `CONTEXT.md`'s "What Exists" list gained one line for this story, matching the existing `tenant-registry`/`query-catalog` bullet style.
- **FCT-6** — `python scripts/dev/generate_code_registry.py` runs against the current tree without error and produces a registry file (mirroring `scratch-script-registry`'s existing registry format)
  listing every script under `investigations/*/scripts`, `experiments/*/scripts`, `src/pipelines`, `src/tools`, and every `src/lib/*` module; its tests cover a fixture tree with two near-duplicate
  scripts and confirm the registry surfaces both. The guide doc states the delegated duplicate-check convention (a sub-agent checks this registry before any new script is written) that
  `project-taxonomy`'s PT-3 depends on.
- **FCT-7** — `src/lib/paths/protocols.py` defines the `PathResolver` `Protocol` (`resolve_input_dir`, `resolve_knowledge_dir`, `resolve_investigation_dir`, `resolve_investigation_data_dir`,
  `resolve_investigation_output_dir`, `format_snapshot_filename`, `format_range_filename`, `format_rollup_filename`) and a concrete `YamlPathResolver` reading `config/data_paths.yaml`'s 7 templates +
  `filename_date_format` (owned by `project-taxonomy`'s PT-7); tests confirm `resolve_input_dir` returns `None` (never raises) when a tool's directory is absent, that `resolve_knowledge_dir` ignores
  campaign/case-id, that all directory templates format correctly, that `format_snapshot_filename`/`format_range_filename` produce the ISO-prefix shapes PT-7 defines (range tag trailing, never
  infix), and that `format_rollup_filename` carries no date; a `Protocol`-conformance test pair matches FCT-2's existing pattern.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per this project's own convention — do not leave a done story half-archived.
