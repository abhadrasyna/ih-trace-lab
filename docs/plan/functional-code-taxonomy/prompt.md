# Functional code taxonomy — prompt

> Define the shared `src/lib/*` module layout (Athena execution, CSV I/O, report rendering, HAR parsing, AWS SSO auth, curl-to-Python conversion) that every pipeline/investigation/tool consumes
> instead of reimplementing, with the riskiest three modules' interfaces designed as `PYTHON_DESIGN.md`-compliant `Protocol`s from the start, plus a cross-project registry that makes checking for an
> existing implementation before writing a new one the fast path, not the disciplined-but-skipped path.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Auditing `/Users/abhadra/github_copilot` (read-only reference, 2026-09-28 session) found the same Athena start/poll/download pattern implemented three separate times with no shared client:
`oasis-athena-mcp/src/athena_mcp/query_tools.py` (MCP-tool-flavored), `ctap-smvod-session-report/scripts/lib/athena_runner.py` (whose own header comment claims "DRY" — but only within that one
project), and `aws-access-cli/scripts/athena_runner/query_executor.py` (a third, independently-built package with its own `aws_clients.py`/`config.py`/`exceptions.py`) — plus a **fourth** independent
copy found later in `mtn-zm-session-device-investigation/scripts/athena_runner/` (with its own `.venv` and `pytest.ini`). CSV/report writing is duplicated ad hoc across at least eight files in five
different projects (`ctap-smvod-session-report`, `aws-access-cli`, `applauseInvestigation`, `mtn-zm-session-device-investigation`, `vod-playback-timing-probe`), with no shared writer anywhere. A
follow-up, function-body-level (not just filename-level) comparison found a third pattern: the same ~5-line "load HAR `log.entries`" loader reimplemented four times — `applauseInvestigation/scripts/
analyze_har.py::iter_entries()`, `vod-playback-timing-probe/scripts/extract_content_ids_from_har.py::_load_entries()`, `vod-playback-timing-probe/scripts/summarize_har_playbacks.py::_load_entries()`
(twice within the *same* project), and `vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()` (the one project that isolated it into its own file — a usable seed, not a
throwaway). This is the single biggest concrete cause of the "redo the same investigation again without knowing a similar one exists" problem this project's mission statement (`README.md`) names.

This story is the functional-code counterpart to `docs/plan/project-taxonomy/`: that story decides *what kind of project* a piece of work is; this one decides *what shared library code* any project —
regardless of category — imports instead of reinventing. It also gives `PYTHON_DESIGN.md` (currently reference-only, "loaded on trigger only") its first concrete trigger: the Athena executor is a
textbook DIP violation (each of the four originals constructs its own `boto3` client internally instead of receiving one), CSV/report writing is a textbook OCP violation (every new report format is a
new copy-pasted `to_csv`/print-loop rather than a new `Strategy` implementer), and HAR-entry loading is a textbook SRP/duplication violation (the loader is a pure domain-mechanism function that has no
business being copy-pasted per project) — this story applies those triggers when designing the three riskiest modules' interfaces, rather than porting the originals' shape as-is.

Auditing further found that the "thin script, import shared lib" convention is not self-enforcing on its own — every one of the four duplicated Athena executors and all four HAR-loader copies existed
inside a project that already claimed to follow that convention. `docs/plan/scratch-script-registry/` already solved exactly this problem for `scratch/` scripts (a sub-agent-delegated duplicate-check
before writing a new probe); FCT-6 generalizes that same registry-and-check pattern to *every* new script anywhere in `ih-trace-lab` (`investigations/*/scripts`, `experiments/*/scripts`,
`src/pipelines`, `src/tools`), since `project-taxonomy`'s PT-3 checklist depends on this registry existing to do its script-level prior-art check.

## Scope guard

**In scope:** a target module map (`docs/guides/functional-code-taxonomy.md`) covering `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/`, with each module's responsibility and which
`github_copilot` original(s) it replaces; a "shared vs. specific" test stating precisely when logic must move to `src/lib/` vs. stay local to one project (FCT-1); `Protocol`-based interface skeletons
(no implementation bodies) for the three highest-risk modules — `athena`, `report_render`, and `har` — with tests asserting they are runtime-checkable `Protocol`s; a migration/ownership table
cross-referencing `docs/plan/project-taxonomy/` (which category consumes which module) and `docs/plan/query-catalog/` (the existing story owning SQL *text* — this story owns query *execution*, not the
SQL itself); a cross-project script registry generator and its delegated duplicate-check convention, generalizing `docs/plan/scratch-script-registry/`'s existing pattern (FCT-6);
`AGENTS.md`/`CONTEXT.md` pointer lines.

**Out of scope:** any change under `/Users/abhadra/github_copilot` (read-only, never edited from this project); actual working implementations of `src/lib/athena/client.py`,
`src/lib/csv_io/writer.py`, etc. — those are real production code with real tests and are deliberately left to follow-up stories triggered the first time an actual pipeline/investigation/tool needs
them, not built speculatively now (this project's YAGNI stance, and `PYTHON_DESIGN.md`'s own closing section: "don't build preemptively... worth building only once there's evidence"); the SQL text
itself, already owned by `docs/plan/query-catalog/`; `project-taxonomy`'s own new-top-level-folder checklist and its Rule A/Rule B nesting rules — this story only supplies the script-level registry
that checklist queries, it does not redefine folder-level rules.

## Session-start load hints

- `PYTHON_DESIGN.md` — read in full before FCT-2; this story's `Protocol` skeletons are the first place this doc's SRP/OCP/DIP triggers and the Strategy pattern get applied in `ih-trace-lab`, not a
  restatement to skip.
- `docs/plan/project-taxonomy/prompt.md` and `structure.md` — the sibling story whose per-category folder skeletons (PT-2) name which modules a pipeline/tool/investigation's `scripts/`/`src/` imports,
  and whose PT-3 new-script checklist depends on FCT-6's registry existing; this story does not re-decide project categories or folder layout.
- `docs/plan/query-catalog/prompt.md` — read its "Why this story exists" section before FCT-3, to state the SQL-text-vs-execution-code boundary precisely rather than guessing at it.
- `docs/plan/scratch-script-registry/prompt.md` and `stories.md` — the existing single-scope (scratch-only) registry/duplicate-check pattern FCT-6 generalizes; match its delegation style and registry
  file format rather than inventing a new one.
- `docs/guides/git-multi-account-auth.md` — this project's existing `docs/guides/*.md` tone/structure precedent.

## Task overview

- **FCT-1** — `docs/guides/functional-code-taxonomy.md`: module map (six `src/lib/*` modules), each with responsibility + which `github_copilot` originals it replaces (audit evidence), plus the
  "shared vs. specific" test for what must be extracted vs. stay local.
- **FCT-2** — `src/lib/athena/protocols.py`, `src/lib/report_render/protocols.py`, and `src/lib/har/protocols.py`: `Protocol`-based interface skeletons per `PYTHON_DESIGN.md`'s DIP/OCP/Strategy
  triggers, with tests.
- **FCT-3** — Same guide doc: migration/ownership table cross-referencing `project-taxonomy` and `query-catalog`, stating the SQL-text-vs-execution-code boundary explicitly.
- **FCT-4** — `AGENTS.md`: one-line pointer noting this guide is where `PYTHON_DESIGN.md`'s triggers get applied concretely.
- **FCT-5** — `CONTEXT.md`: one new "What Exists" line.
- **FCT-6** — `scripts/dev/generate_code_registry.py` + doc section: a cross-project script/module registry (extending `scratch-script-registry`'s scratch-only registry to `investigations/*/scripts`,
  `experiments/*/scripts`, `src/pipelines`, `src/tools`, and `src/lib/*` itself) plus the delegated duplicate-check convention `project-taxonomy`'s PT-3 relies on.

## Definition of done

- `docs/guides/functional-code-taxonomy.md` names all six modules, each with a concrete replaced-original citation from the 2026-09-28 audit, states the "shared vs. specific" test, and does not
  contradict `docs/plan/project-taxonomy/`'s folder skeletons or `structure.md`.
- `src/lib/athena/protocols.py`, `src/lib/report_render/protocols.py`, and `src/lib/har/protocols.py` exist as `Protocol` definitions only (no concrete implementation), each `@runtime_checkable` where
  that is meaningful, with passing tests confirming a minimal conforming stub satisfies the `Protocol`.
- The guide doc states, in one place, which future story owns SQL text (`query-catalog`) vs. execution code (this story) — no reader has to infer the boundary.
- `scripts/dev/generate_code_registry.py` runs against the current (empty) tree without error, and the guide doc states the delegated duplicate-check convention `project-taxonomy`'s PT-3 depends on.
- `AGENTS.md` and `CONTEXT.md` each gained exactly one new pointer line.
- No file under `/Users/abhadra/github_copilot` was created, edited, or deleted by this story.

## Perspectives not covered

- This story does not build the `curl_to_python` or `auth`/`csv_io` modules' `Protocol` skeletons — only `athena`, `report_render`, and `har` get that treatment now, because those are the three with
  proven, audited triplicate/octuplicate/quadruplicate duplication; the remaining modules get the same treatment as a follow-up once a real consumer needs them, per this story's own YAGNI stance
  stated above — treat that as a deliberate scope cut, not an oversight.
