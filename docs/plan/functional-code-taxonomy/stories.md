# Functional code taxonomy — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `PYTHON_DESIGN.md`. After each task: set `SHA:` on the
> task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

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
   - **`src/lib/har/`** — HAR capture parsing, shared by `mtn-network-traffic` and `vod-playback-timing-probe`-style network-timing work.
   - **`src/lib/curl_to_python/`** — the curl-command-to-Python-code converter itself (from `mtn-network-traffic`), reusable across any future traffic-capture project rather than being that one
     project's private script.
3. Each subsection ends with one line: "not yet implemented — first real port happens when a follow-up story needs it" (this story only maps the target, per its own Scope guard).

**Tests:** none — docs-only.

**Commit:** `docs(functional-code-taxonomy): define the six shared-lib modules`

---

## FCT-2 — `src/lib/athena/protocols.py` + `src/lib/report_render/protocols.py`: `Protocol` skeletons + tests

**Files to change / create:**
- `src/lib/__init__.py`, `src/lib/athena/__init__.py`, `src/lib/report_render/__init__.py` (per `AGENTS.md`'s package convention — every new package directory needs an `__init__.py`)
- `src/lib/athena/protocols.py`
- `src/lib/report_render/protocols.py`
- `tests/lib/athena/test_protocols.py`, `tests/lib/report_render/test_protocols.py`, plus any missing `__init__.py` under `tests/`

**What to implement (per `PYTHON_DESIGN.md`'s DIP and OCP/Strategy triggers — interfaces only, no bodies beyond `...`, type hints on every signature):**

1. `src/lib/athena/protocols.py`:
   - `QueryResult` — a small typed data container (e.g. `dataclass` or `TypedDict`) holding at least `query_execution_id: str`, `rows: list[dict[str, str]]`, `state: str`.
   - `AthenaClient(Protocol)` `@runtime_checkable` — the DIP seam: `start_query(sql: str, params: Mapping[str, str]) -> str` (returns execution id), `poll_status(execution_id: str) -> str`,
     `fetch_results(execution_id: str) -> QueryResult`. This is what every one of the three duplicated originals should have received via `__init__` instead of constructing `boto3.client("athena")`
     itself — the DIP trigger from `PYTHON_DESIGN.md` applied directly.
   - Docstring on the `Protocol` stating explicitly which three `github_copilot` originals this seam is meant to replace (cross-reference FCT-1, do not re-describe them).
2. `src/lib/report_render/protocols.py`:
   - `ReportRenderer(Protocol)` `@runtime_checkable` — the OCP/Strategy seam: `render(rows: list[dict[str, str]]) -> str`. A new output format (CSV, markdown table, summary text) is a new implementer
     of this `Protocol`, never a new `elif` branch inside one function — the OCP trigger from `PYTHON_DESIGN.md` applied directly.
   - Docstring naming this as the Strategy pattern per `PYTHON_DESIGN.md`'s "Named patterns" section, cross-referencing FCT-1's `csv_io`/`report_render` split (rendering is a `Strategy` over already
     read/normalized rows; `csv_io` owns getting rows in/out of files, not formatting them).

**Tests (no network, no real files outside `tmp_path` where relevant):**
- `test_protocols.py` (athena): `test_conforming_stub_satisfies_athena_client_protocol` (a minimal hand-written class implementing all three methods passes `isinstance(stub, AthenaClient)`) /
  `test_non_conforming_stub_does_not_satisfy_protocol` (a class missing one method fails the `isinstance` check).
- `test_protocols.py` (report_render): `test_conforming_stub_satisfies_report_renderer_protocol` / `test_non_conforming_stub_does_not_satisfy_protocol`.

**Commit:** `feat(functional-code-taxonomy): add athena and report_render Protocol skeletons`

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

1. One new bullet, same style as the existing `tenant-registry`/`query-catalog` bullets: story slug, one-line summary (six-module shared-lib map + two `Protocol` skeletons replacing triplicated Athena
   execution and duplicated CSV/report writing), current status (reference the first unchecked task id at the time this task runs, or "implemented" if FCT-1 through FCT-4 are all done).

**Tests:** none — docs-only.

**Commit:** `docs(functional-code-taxonomy): add CONTEXT.md entry`
