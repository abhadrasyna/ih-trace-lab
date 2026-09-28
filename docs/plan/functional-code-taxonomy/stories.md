# Functional code taxonomy — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `PYTHON_DESIGN.md`. After each task: set `SHA:` on the
> task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

See `docs/plan/project-taxonomy/structure.md` for the canonical target folder tree this story's `src/lib/*` modules and FCT-6's registry must stay consistent with — do not restate that tree here;
cross-reference it by name.

---

## FCT-1 — `docs/guides/functional-code-taxonomy.md`: six-module map + replaced-originals evidence

**Files to change / create:**
- `docs/guides/functional-code-taxonomy.md` — new file

**What to implement:**

1. Header matching `docs/guides/git-multi-account-auth.md`'s tone (short intro, no plan-tracking checkboxes — reference doc, not a story file).
2. A `## Modules` section, one subsection per module, each stating responsibility + replaced original(s):
   - **`src/lib/auth/`** — AWS SSO session refresh. Replaces `github_copilot/aws-access-cli/scripts/refresh_aws_sso.py`.
   - **`src/lib/athena/`** — Athena query start/poll/download, one canonical client. Replaces `github_copilot/oasis-athena-mcp/src/athena_mcp/query_tools.py`,
     `github_copilot/ctap-smvod-session-report/scripts/lib/athena_runner.py`, and `github_copilot/aws-access-cli/scripts/athena_runner/query_executor.py` (three independent implementations of the same
     start_query_execution/poll/get_query_results pattern).
   - **`src/lib/csv_io/`** — shared CSV/report reader+writer. Replaces the ad hoc `to_csv`/`csv.DictWriter` blocks found in `ctap-smvod-session-report` (multiple scripts), `aws-access-cli`
     (`run_incomplete_no_destroy_investigation.py`, `run_adoption_gap_analysis_report.py`, `run_adoption_gap_analysis_session_report.py`, `athena_runner/adoption/period_report_store.py`,
     `athena_runner/adoption/report_store.py`), `applauseInvestigation/scripts/analyze_athena_playback.py`, `mtn-zm-session-device-investigation` (multiple scripts), and
     `mtn-network-traffic/scripts/curl_timer/report.py`.
   - **`src/lib/report_render/`** — table/markdown/summary rendering shared by any pipeline/investigation report runner, built on `csv_io`.
   - **`src/lib/har/`** — HAR capture entry-loading and normalization. Replaces the identical "load `har["log"]["entries"]`" loader function found duplicated four times, function-body-level (not just
     by name): `applauseInvestigation/scripts/analyze_har.py::iter_entries()`, `vod-playback-timing-probe/scripts/extract_content_ids_from_har.py::_load_entries()`, `vod-playback-timing-
     probe/scripts/summarize_har_playbacks.py::_load_entries()` (a *second* copy inside the same project), and `vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()` (the one
     project that isolated it — a usable seed, not a throwaway).
   - **`src/lib/curl_to_python/`** — the curl-command-to-Python-code converter itself (from `mtn-network-traffic`), reusable across any future traffic-capture project rather than being that one
     project's private script.
3. Each subsection ends with one line: "not yet implemented — first real port happens when a follow-up story needs it" (this story only maps the target, per its own Scope guard).
4. A `## Shared vs. specific test` section stating the rule precisely, since it is what `project-taxonomy`'s PT-3 checklist and FCT-6's registry check both invoke when a search finds a near-match:
   logic belongs in `src/lib/` **if and only if** it operates on a domain mechanism — a technical concern that is the same regardless of which campaign/case/pipeline is asking (Athena query execution,
   CSV/report I/O, HAR entry parsing, curl-command parsing, AWS SSO refresh). Logic stays local to one project's `scripts/` **if** it encodes a campaign- or case-specific business rule — which fields
   matter for *this* ticket, what counts as an anomaly for *this* customer, how *this* report should be titled. The test is not "does another project already have similar code" (that is just evidence
   a shared module is now overdue) — it is "would a second, unrelated project plausibly need the exact same logic to answer a *different* business question." If yes, it is a `src/lib/` candidate *by
   definition*, regardless of which project needs it first; do not wait for a second occurrence before extracting a *newly written* domain-mechanism function (the "wait for evidence" YAGNI stance in
   this story's Scope guard applies to which modules get built now, not to whether a brand-new domain-mechanism function should be written directly in `src/lib/` when its nature is already obvious).

**Tests:** none — docs-only.

**Commit:** `docs(functional-code-taxonomy): define the six shared-lib modules`

---

## FCT-2 — `src/lib/{athena,report_render,har}/protocols.py`: `Protocol` skeletons + tests

**Files to change / create:**
- `src/lib/__init__.py`, `src/lib/athena/__init__.py`, `src/lib/report_render/__init__.py`, `src/lib/har/__init__.py` (per `AGENTS.md`'s package convention — every new package directory needs an
  `__init__.py`)
- `src/lib/athena/protocols.py`
- `src/lib/report_render/protocols.py`
- `src/lib/har/protocols.py`
- `tests/lib/athena/test_protocols.py`, `tests/lib/report_render/test_protocols.py`, `tests/lib/har/test_protocols.py`, plus any missing `__init__.py` under `tests/`

**What to implement (per `PYTHON_DESIGN.md`'s DIP and OCP/Strategy triggers — interfaces only, no bodies beyond `...`, type hints on every signature):**

1. `src/lib/athena/protocols.py`:
   - `QueryResult` — a small typed data container (e.g. `dataclass` or `TypedDict`) holding at least `query_execution_id: str`, `rows: list[dict[str, str]]`, `state: str`.
   - `AthenaClient(Protocol)` `@runtime_checkable` — the DIP seam: `start_query(sql: str, params: Mapping[str, str]) -> str` (returns execution id), `poll_status(execution_id: str) -> str`,
     `fetch_results(execution_id: str) -> QueryResult`. This is what every one of the four duplicated originals should have received via `__init__` instead of constructing `boto3.client("athena")`
     itself — the DIP trigger from `PYTHON_DESIGN.md` applied directly.
   - Docstring on the `Protocol` stating explicitly which four `github_copilot` originals this seam is meant to replace (cross-reference FCT-1, do not re-describe them).
2. `src/lib/report_render/protocols.py`:
   - `ReportRenderer(Protocol)` `@runtime_checkable` — the OCP/Strategy seam: `render(rows: list[dict[str, str]]) -> str`. A new output format (CSV, markdown table, summary text) is a new implementer
     of this `Protocol`, never a new `elif` branch inside one function — the OCP trigger from `PYTHON_DESIGN.md` applied directly.
   - Docstring naming this as the Strategy pattern per `PYTHON_DESIGN.md`'s "Named patterns" section, cross-referencing FCT-1's `csv_io`/`report_render` split (rendering is a `Strategy` over already
     read/normalized rows; `csv_io` owns getting rows in/out of files, not formatting them).
3. `src/lib/har/protocols.py`:
   - `HarEntry` — a small typed data container for one normalized HAR log entry (at least `url: str`, `method: str`, `status: int`, `started_datetime: str`).
   - `HarEntryLoader(Protocol)` `@runtime_checkable` — the SRP/duplication seam: `load_entries(har_path: Path) -> list[HarEntry]`. This is the seam every one of the four duplicated
     `iter_entries`/`_load_entries`/`load_json_entries` functions should have shared instead of each project (and, in `vod-playback-timing-probe`'s case, each *script*) reimplementing the same
     `har["log"]["entries"]` walk. Docstring seeds its shape from `vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()` (read-only reference — inspect its field names, do not
     copy its code verbatim) and names all four duplicated originals this seam replaces.

**Tests (no network, no real files outside `tmp_path` where relevant):**
- `test_protocols.py` (athena): `test_conforming_stub_satisfies_athena_client_protocol` (a minimal hand-written class implementing all three methods passes `isinstance(stub, AthenaClient)`) /
  `test_non_conforming_stub_does_not_satisfy_protocol` (a class missing one method fails the `isinstance` check).
- `test_protocols.py` (report_render): `test_conforming_stub_satisfies_report_renderer_protocol` / `test_non_conforming_stub_does_not_satisfy_protocol`.
- `test_protocols.py` (har): `test_conforming_stub_satisfies_har_entry_loader_protocol` / `test_non_conforming_stub_does_not_satisfy_protocol`.

**Commit:** `feat(functional-code-taxonomy): add athena, report_render, and har Protocol skeletons`

---

## FCT-3 — same doc: migration/ownership table + query-catalog boundary

**Files to change / create:**
- `docs/guides/functional-code-taxonomy.md` — append to the file from FCT-1

**What to implement:**

1. A `## Which category consumes which module` table, columns `Project category (docs/plan/project-taxonomy) | Modules it typically imports`:
   - Pipeline → `athena`, `csv_io`, `report_render`, `auth`.
   - Continuous investigation → `athena`, `csv_io`, `report_render`, `har` (if network-capture based).
   - One-off investigation → same as continuous investigation, thinner usage.
   - Tool → depends on the tool; `oasis-athena-mcp`-equivalent tools become adapters over `athena` rather than owning their own client.
   - Experiment → whichever module the probe's question touches; still imports rather than reimplements, per the "thin consumer" rule stated in `docs/plan/project-taxonomy/`.
2. One explicit sentence, verbatim-quotable: "`docs/plan/query-catalog` owns the SQL text (deduplicated, parameterized query templates); this story owns the code that executes that SQL
   (`src/lib/athena/`) — a query template is a string passed into `AthenaClient.start_query`, never duplicated logic inside this module." Read `docs/plan/query-catalog/prompt.md`'s "Why this story
   exists" section before writing this sentence, so the boundary matches that story's actual stated scope rather than an assumption.

**Tests:** none — docs-only.

**Commit:** `docs(functional-code-taxonomy): add category/module table and query-catalog boundary`

---

## FCT-4 — `AGENTS.md` pointer line

**Files to change / create:**
- `AGENTS.md` — the existing Python conventions section (near wherever `PYTHON_DESIGN.md` is already referenced)

**What to implement:**

1. One sentence pointing to `docs/guides/functional-code-taxonomy.md` as where `PYTHON_DESIGN.md`'s SRP/OCP/DIP triggers get applied concretely to this project's shared-lib design, placed next to the
   existing `PYTHON_DESIGN.md` pointer line so both docs are discoverable from the same spot. No module list or `Protocol` detail duplicated into `AGENTS.md`.

**Tests:** none — docs-only.

**Commit:** `docs(functional-code-taxonomy): point AGENTS.md at the new guide`

---

## FCT-5 — `CONTEXT.md` pointer line

**Files to change / create:**
- `CONTEXT.md` — "What Exists" list

**What to implement:**

1. One new bullet, same style as the existing `tenant-registry`/`query-catalog` bullets: story slug, one-line summary (six-module shared-lib map + three `Protocol` skeletons replacing quadruplicated
   Athena execution, duplicated CSV/report writing, and quadruplicated HAR-entry loading, plus a cross-project script registry), current status (reference the first unchecked task id at the time this
   task runs, or "implemented" if FCT-1 through FCT-7 are all done).

**Tests:** none — docs-only.

**Commit:** `docs(functional-code-taxonomy): add CONTEXT.md entry`

---

## FCT-6 — `scripts/dev/generate_code_registry.py` + doc section: cross-project registry + delegated duplicate-check

**Files to change / create:**
- `scripts/dev/generate_code_registry.py` — new file
- `tests/dev/test_generate_code_registry.py` — new file, using a fixture tree under `tmp_path` (no scan of the real repo in tests)
- `docs/guides/functional-code-taxonomy.md` — append a `## Cross-project script registry` section

**What to implement:**

1. `scripts/dev/generate_code_registry.py`: walks `investigations/*/scripts`, `experiments/*/scripts`, `src/pipelines`, `src/tools`, and `src/lib/*`, and writes a registry file (mirroring
   `docs/plan/scratch-script-registry/`'s existing registry format and generator style exactly — read that story's generator before writing this one; do not invent a new format) listing, per script:
   path, top-level function/class names, and a short docstring-derived summary if present. This generalizes that story's scratch-only registry to every new-script location named in
   `project-taxonomy`'s PT-3 checklist.
2. The registry generator does not attempt semantic duplicate detection itself (that is a sub-agent's job, per point 3) — it only produces the searchable inventory a sub-agent greps/reads before
   writing a new script.
3. `## Cross-project script registry` section in the guide doc: states the delegated duplicate-check convention `project-taxonomy`'s PT-3 step 3 invokes — before writing any new script, delegate a
   sub-agent to search this registry (and `src/lib/*`'s existing modules) for a function performing the same or closely related operation, giving it the concrete operation name (e.g. "load HAR log
   entries", "write a CSV report"), not the project name. Cross-reference FCT-1's "shared vs. specific" test for what to do when a near-match is found: promote to `src/lib/` if the match is a domain
   mechanism, leave as-is if it is genuinely campaign/case-specific.
4. Cite the concrete evidence motivating this generalization in the doc section: all four duplicated Athena executors and all four duplicated HAR-entry loaders existed inside projects that already
   claimed to follow a "thin script, import shared lib" convention — the convention alone did not prevent the duplication; a registry + mandatory delegated check is what makes reuse the fast path.

**Tests:**
- `test_generate_code_registry.py`: fixture tree with two near-duplicate scripts (same function name/signature, different bodies) under two different fixture project folders; assert the generated
  registry lists both, and that a human/sub-agent reading it would spot the name collision without needing to open either file's body.
- One test confirming the generator runs against an empty fixture tree without error (mirrors PT-4's own "runs against the current empty `ih-trace-lab` tree" requirement).

**Commit:** `feat(functional-code-taxonomy): add cross-project script registry and duplicate-check convention`

---

## FCT-7 — `src/lib/paths/protocols.py` + resolver: config-driven data/knowledge/investigations path resolution

**Grounding:** found during the 2026-09-28 discussion round designing `project-taxonomy`'s PT-7 (`config/data_paths.yaml`, root `data/` tree, `docs/`-vs-`knowledge/` distinction). The layout debate
itself (tool-first vs. campaign-first `data/` nesting, whether a `misc/` bucket is needed) changed direction twice in one discussion — concrete evidence that no script should ever hardcode this
shape; every script must resolve it from `config/data_paths.yaml` through one shared module instead.

**Files to change / create:**
- `src/lib/paths/__init__.py` (per `AGENTS.md`'s package convention)
- `src/lib/paths/protocols.py`
- `src/lib/paths/config.py` — loads and validates `config/data_paths.yaml`
- `tests/lib/paths/test_protocols.py`, `tests/lib/paths/__init__.py` if not already created by another story

**What to implement (per `PYTHON_DESIGN.md`'s DIP trigger — the config file is the seam, not a hardcoded dict):**

1. `PathConfig` — a small typed data container loaded from `config/data_paths.yaml` (`data_root`, `knowledge_root`, `investigations_root`, `tools: tuple[str, ...]`, and the 5 template strings named
   in `project-taxonomy`'s PT-7: `data_with_campaign`, `data_without_campaign`, `knowledge`, `investigation_with_campaign`, `investigation_without_campaign`).
2. `PathResolver(Protocol)` `@runtime_checkable` exposing:
   - `resolve_input_dir(tool: str, case_id: str, campaign: str | None = None) -> Path | None` — formats `data_with_campaign` or `data_without_campaign` depending on whether `campaign` is given, and
     returns `None` (never raises) if the resulting directory does not exist on disk — absence of a saved export for a tool is a normal, expected state (HAR-only cases, manual-only Lightstep/Athena
     queries), not an error condition. Callers branch on `None` explicitly.
   - `resolve_knowledge_dir(tool: str) -> Path` — formats `knowledge`; always returns a path (creating the directory is the caller's job, not the resolver's), never takes a `campaign`/`case_id` — this
     axis is deliberately tool-first and case-independent, per `structure.md`'s `knowledge/` block.
   - `resolve_investigation_dir(case_id: str, campaign: str | None = None) -> Path` — formats `investigation_with_campaign` or `investigation_without_campaign`; the caller appends the fixed
     `docs/`/`queries/`/`scripts/`/`tests/` skeleton from `project-taxonomy`'s PT-2 — that skeleton is not templated, only the root segment is.
3. A concrete `YamlPathResolver` implementing the `Protocol`, reading `config/data_paths.yaml` via `PathConfig`. No other module in this repo constructs a `data/`, `knowledge/`, or `investigations/`
   path via raw string concatenation once this exists — that is the enforcement point PT-3's prior-art checklist and FCT-6's registry check both rely on for this specific case.

**Tests (no network, no real repo paths outside `tmp_path`):**
- `test_resolve_input_dir_with_campaign_formats_data_with_campaign_template`
- `test_resolve_input_dir_without_campaign_formats_data_without_campaign_template`
- `test_resolve_input_dir_returns_none_when_directory_absent` — the core contract: a missing HAR/Lightstep/Athena folder is `None`, not an exception.
- `test_resolve_knowledge_dir_ignores_campaign_and_case_id` — confirms the tool-first axis takes no case/campaign arguments even if accidentally passed.
- `test_resolve_investigation_dir_with_and_without_campaign`
- `test_conforming_stub_satisfies_path_resolver_protocol` / `test_non_conforming_stub_does_not_satisfy_protocol` (matches FCT-2's existing `Protocol`-conformance test pattern).

**Commit:** `feat(functional-code-taxonomy): add src/lib/paths config-driven resolver`
