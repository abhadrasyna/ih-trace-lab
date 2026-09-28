# Functional code taxonomy — prompt

> Define the shared `src/lib/*` module layout (Athena execution, CSV I/O, report rendering, HAR parsing, AWS SSO auth, curl-to-Python conversion) that every pipeline/investigation/tool consumes
> instead of reimplementing, with the riskiest two modules' interfaces designed as `PYTHON_DESIGN.md`-compliant `Protocol`s from the start.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Auditing `/Users/abhadra/github_copilot` (read-only reference, 2026-09-28 session) found the same Athena start/poll/download pattern implemented three separate times with no shared client:
`oasis-athena-mcp/src/athena_mcp/query_tools.py` (MCP-tool-flavored), `ctap-smvod-session-report/scripts/lib/athena_runner.py` (whose own header comment claims "DRY" — but only within that one
project), and `aws-access-cli/scripts/athena_runner/query_executor.py` (a third, independently-built package with its own `aws_clients.py`/`config.py`/`exceptions.py`). CSV/report writing is
duplicated ad hoc across at least eight files in five different projects (`ctap-smvod-session-report`, `aws-access-cli`, `applauseInvestigation`, `mtn-zm-session-device-investigation`,
`vod-playback-timing-probe`), with no shared writer anywhere. This is the single biggest concrete cause of the "redo the same investigation again without knowing a similar one exists" problem this
project's mission statement (`README.md`) names.

This story is the functional-code counterpart to `docs/plan/project-taxonomy/`: that story decides *what kind of project* a piece of work is; this one decides *what shared library code* any project —
regardless of category — imports instead of reinventing. It also gives `PYTHON_DESIGN.md` (currently reference-only, "loaded on trigger only") its first concrete trigger: the Athena executor is a
textbook DIP violation (each of the three originals constructs its own `boto3` client internally instead of receiving one), and CSV/report writing is a textbook OCP violation (every new report format
is a new copy-pasted `to_csv`/print-loop rather than a new `Strategy` implementer) — this story applies those triggers when designing the two riskiest modules' interfaces, rather than porting the
originals' shape as-is.

## Scope guard

**In scope:** a target module map (`docs/guides/functional-code-taxonomy.md`) covering `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/`, with each module's responsibility and which
`github_copilot` original(s) it replaces; `Protocol`-based interface skeletons (no implementation bodies) for the two highest-risk modules — `athena` and `report_render` — with tests asserting they
are runtime-checkable `Protocol`s; a migration/ownership table cross-referencing `docs/plan/project-taxonomy/` (which category consumes which module) and `docs/plan/query-catalog/` (the existing story
owning SQL *text* — this story owns query *execution*, not the SQL itself); `AGENTS.md`/`CONTEXT.md` pointer lines.

**Out of scope:** any change under `/Users/abhadra/github_copilot` (read-only, never edited from this project); actual working implementations of `src/lib/athena/client.py`,
`src/lib/csv_io/writer.py`, etc. — those are real production code with real tests and are deliberately left to follow-up stories triggered the first time an actual pipeline/investigation/tool needs
them, not built speculatively now (this project's YAGNI stance, and `PYTHON_DESIGN.md`'s own closing section: "don't build preemptively... worth building only once there's evidence"); the SQL text
itself, already owned by `docs/plan/query-catalog/`.

## Session-start load hints

- `PYTHON_DESIGN.md` — read in full before FCT-2; this story's `Protocol` skeletons are the first place this doc's SRP/OCP/DIP triggers and the Strategy pattern get applied in `ih-trace-lab`, not a
  restatement to skip.
- `docs/plan/project-taxonomy/prompt.md` — the sibling story whose per-category folder skeletons (PT-2) name which modules a pipeline/tool/investigation's `scripts/`/`src/` imports; this story does
  not re-decide project categories.
- `docs/plan/query-catalog/prompt.md` — read its "Why this story exists" section before FCT-3, to state the SQL-text-vs-execution-code boundary precisely rather than guessing at it.
- `docs/guides/git-multi-account-auth.md` — this project's existing `docs/guides/*.md` tone/structure precedent.

## Task overview

- **FCT-1** — `docs/guides/functional-code-taxonomy.md`: module map (six `src/lib/*` modules), each with responsibility + which `github_copilot` originals it replaces (audit evidence).
- **FCT-2** — `src/lib/athena/protocols.py` and `src/lib/report_render/protocols.py`: `Protocol`-based interface skeletons per `PYTHON_DESIGN.md`'s DIP/OCP/Strategy triggers, with tests.
- **FCT-3** — Same guide doc: migration/ownership table cross-referencing `project-taxonomy` and `query-catalog`, stating the SQL-text-vs-execution-code boundary explicitly.
- **FCT-4** — `AGENTS.md`: one-line pointer noting this guide is where `PYTHON_DESIGN.md`'s triggers get applied concretely.
- **FCT-5** — `CONTEXT.md`: one new "What Exists" line.

## Definition of done

- `docs/guides/functional-code-taxonomy.md` names all six modules, each with a concrete replaced-original citation from the 2026-09-28 audit, and does not contradict `docs/plan/project-taxonomy/`'s
  folder skeletons.
- `src/lib/athena/protocols.py` and `src/lib/report_render/protocols.py` exist as `Protocol` definitions only (no concrete implementation), each `@runtime_checkable` where that is meaningful, with
  passing tests confirming a minimal conforming stub satisfies the `Protocol`.
- The guide doc states, in one place, which future story owns SQL text (`query-catalog`) vs. execution code (this story) — no reader has to infer the boundary.
- `AGENTS.md` and `CONTEXT.md` each gained exactly one new pointer line.
- No file under `/Users/abhadra/github_copilot` was created, edited, or deleted by this story.

## Perspectives not covered

- This story does not build the `har` or `curl_to_python` module's `Protocol` skeletons — only `athena` and `report_render` get that treatment now, because those are the two with proven, audited
  triplicate/octuplicate duplication; `har`/`curl_to_python`/`auth`/`csv_io` get the same treatment as a follow-up once a real consumer needs them, per this story's own YAGNI stance stated above —
  treat that as a deliberate scope cut, not an oversight.
