# Src-lib migration — epic index

> Deliver the real, tested implementations behind `functional-code-taxonomy`'s `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/` module map — porting/refactoring duplicated logic out of
> `/Users/abhadra/github_copilot` (read-only reference) module by module — plus, for `athena` specifically, wiring in the already-independent `athena-mcp-server` repo as a git submodule rather than
> re-porting code a sibling project already solved. One epic because all six stories share the same blocking dependency, the same read-only-reference constraint, and the same `PYTHON_DESIGN.md`
> Protocol-first design discipline; six stories because each module has its own originals, its own risk profile, and lands independently.

## Why this epic exists

`docs/archive/functional-code-taxonomy/` (design-only: module map, `Protocol` skeletons for the three riskiest modules, a cross-project script registry) deliberately left every *concrete*
implementation to a follow-up, "triggered the first time an actual pipeline/investigation/tool needs them" (its own stated YAGNI stance). This epic is that follow-up, authorized explicitly rather than
waiting for an organic trigger.

While scoping story 1 (`athena`), auditing `/Users/abhadra/myWork/myOffice/athena-mcp-server` found the athena duplication problem already solved *outside* `ih-trace-lab`: it is a fully independent,
tested (101 tests), pip-installable repo (`src/athena_runner/*`: `config`, `aws_clients`, `query_executor`, `result_downloader`, `sso_auth`, `sso_profiles`, `tenants`, `logging_setup`, `date_utils`,
`exceptions`) already ported from `github_copilot/oasis-athena-mcp` (itself ported from `aws-access-cli/scripts/athena_runner/`). It is not yet wired into `ih-trace-lab` as a submodule. Re-porting
that logic a *fifth* time would recreate the exact problem `functional-code-taxonomy` exists to stop. So `athena-lib-integration` wires the existing submodule in and adapts to it; it does not
reimplement.

## Scope decisions

- **Blocked on `functional-code-taxonomy`.** No story in this epic starts implementation before `functional-code-taxonomy`'s FCT-1 (module map), FCT-2 (`athena`/`report_render`/`har` `Protocol`
  skeletons), and FCT-7 (`PathResolver`) land — this epic implements *against* those artifacts, it does not redesign them. Confirmed with the epic requester, 2026-09-30.
- **`athena` is integration, not migration.** `athena-lib-integration` adds `athena-mcp-server` as a git submodule and writes a thin adapter; it does not port `query_executor.py`/`aws_clients.py`
  logic into `ih-trace-lab` a second time.
- **The other five modules are real ports.** `report_render`, `har`, `auth`, `csv_io`, `curl_to_python` each get a concrete implementation in `src/lib/<module>/`, migrated/refactored (not copied
  verbatim) from their `github_copilot` originals, following the shape `PYTHON_DESIGN.md` prescribes (`Protocol`-based DI, Strategy/Template Method where a decision trigger applies).
- **`auth`, `csv_io`, `curl_to_python` gain their `Protocol` skeletons here**, not in `functional-code-taxonomy` — that story explicitly deferred those three "as a follow-up once a real consumer needs
  them"; this epic is that consumer. Each such story's first task defines the `Protocol` before the concrete class, mirroring FCT-2's own pattern.
- **Diagrams are authored now, at design time**, not deferred to the implementing session: each story below carries a Mermaid class diagram (Protocol + concrete implementer) and a Mermaid sequence
  diagram (primary runtime flow) in its own `stories.md`. This document carries the epic-level architecture diagram.
- **No file under `/Users/abhadra/github_copilot` is ever created, edited, or deleted** by any story in this epic — read-only reference throughout, per this project's `CONTEXT.md` constraint.

## Architecture

```mermaid
graph TB
    subgraph ih_trace_lab["ih-trace-lab"]
        subgraph src_lib["src/lib/*"]
            AUTH["auth/\n(AUM)"]
            ATH["athena/\n(ALI — thin adapter)"]
            CSV["csv_io/\n(CIM)"]
            REPORT["report_render/\n(RRM)"]
            HAR["har/\n(HLM)"]
            CURL["curl_to_python/\n(CPM)"]
        end
        CONSUMERS["future pipelines / investigations / tools\n(project-taxonomy categories)"]
    end

    subgraph submodule["git submodule (new)"]
        AMS["athena-mcp-server\nsrc/athena_runner/*"]
    end

    subgraph aws["AWS"]
        STS["STS / SSO"]
        ATHENA_SVC["Athena / Glue / S3"]
    end

    subgraph reference["/Users/abhadra/github_copilot (read-only reference — never edited)"]
        R1["ctap-smvod-session-report\naws-access-cli\napplauseInvestigation"]
        R2["mtn-zm-session-device-investigation\nvod-playback-timing-probe\nvod-asset-ingestion-mapping"]
    end

    ATH -->|adapts, does not reimplement| AMS
    AMS --> STS
    AMS --> ATHENA_SVC

    REPORT -.->|ported / refactored from| R1
    HAR -.->|ported / refactored from| R2
    AUTH -.->|ported / refactored from| R1
    CSV -.->|ported / refactored from| R2
    CURL -.->|ported / refactored from| R1

    CONSUMERS --> AUTH
    CONSUMERS --> ATH
    CONSUMERS --> CSV
    CONSUMERS --> REPORT
    CONSUMERS --> HAR
    CONSUMERS --> CURL
```

## Stories

| Story | Purpose | Status | Depends on | Closing SHA |
|---|---|---|---|---|
| `athena-lib-integration/` | Submodule `athena-mcp-server` + thin `src/lib/athena/` adapter | ✅ Done | `functional-code-taxonomy` FCT-1/FCT-2 | 43ca081 |
| `report-render-lib-migration/` | Port 8+ duplicated CSV/report writers → `src/lib/report_render/` | 🔄 RRM-1–4 done, RRM-5 open | `functional-code-taxonomy` FCT-1/FCT-2 | — |
| `har-lib-migration/` | Port 4 duplicated HAR-entry loaders → `src/lib/har/` | 🔄 HLM-1 done, HLM-2–4 open | `functional-code-taxonomy` FCT-1/FCT-2 | — |
| `auth-lib-migration/` | Consolidate AWS SSO auth helpers → `src/lib/auth/` (new `Protocol`) | ⬜ Not started | FCT-1, `athena-lib-integration` (reuses `sso_auth` shape) | — |
| `csv-io-lib-migration/` | Consolidate raw CSV I/O → `src/lib/csv_io/` (new `Protocol`) | ⬜ Not started | `functional-code-taxonomy` FCT-1 | — |
| `curl-to-python-lib-migration/` | Consolidate curl→Python conversion → `src/lib/curl_to_python/` (new `Protocol`) | ⬜ Not started | `functional-code-taxonomy` FCT-1 | — |

Status: ⬜ Not started · 🔄 In progress · ✅ Done. This column is the epic's progress view — per-task checkboxes live only in each sub-story's `tasks.md`.

## Cross-cutting constraints

- Every story cites `PYTHON_DESIGN.md`'s specific trigger it applies (most commonly DIP: constructor-injected collaborators, never self-constructed) in its own `stories.md`, not just a generic
  reference to the doc.
- Every story's `Protocol` (new or FCT-2-supplied) is `@runtime_checkable` where instance checks are meaningful, with a conformance test pair (a minimal conforming stub passes `isinstance`, a
  non-conforming one fails) — matches FCT-2's existing pattern exactly.
- No story adds a project-specific business rule to `src/lib/*` — only domain-mechanism logic (Athena execution, CSV/report I/O, HAR parsing, auth, curl conversion) belongs here; anything
  campaign/case-specific stays local to a future consumer's own `scripts/`.
- No live AWS/network calls in any story's tests — mocked `boto3`/filesystem only, matching `athena-mcp-server`'s own existing test convention.
- **2026-10-01 (standardized by `pre-implementation-design-review`, finding #2):** every adapter/implementer's test suite asserts **both** of the following, not just one — (a) constructing the class
  without its required collaborator arguments raises (no silent default construction), and (b) the class makes no direct call to the real external client/library it wraps (`boto3`, the injected
  submodule, etc.) from inside its own methods. `athena-lib-integration`'s ALI-3 and `auth-lib-migration`'s AUM-3 each previously asserted only one half of this pair; both should add the missing
  assertion when picked up.
- **2026-10-01 (extended design review — exception-hierarchy-per-module):** every `src/lib/<module>/` that wraps a third-party or submodule dependency defines its own `exceptions.py` with a single
  module-specific base (e.g. `AthenaAdapterError`) and narrow subclasses, and **never lets the wrapped library's own exception types cross the module's public `Protocol` boundary** — callers catch
  only this module's hierarchy, never `botocore.exceptions.ClientError` or `athena_runner.exceptions.*` directly. `athena-lib-integration`'s `src/lib/athena/exceptions.py` (ALI-2) is the first
  instance of this pattern; `auth-lib-migration`, `csv-io-lib-migration`, `curl-to-python-lib-migration`, and `har-lib-migration` must each add an equivalent `exceptions.py` rather than letting
  `boto3`/filesystem/parsing errors leak through unwrapped.
- **2026-10-01 (extended design review — config-management consistency):** `src/lib/paths/config.py`'s `PathConfig` (a frozen dataclass loaded from YAML via a `.load(path)` classmethod) is this
  project's existing config-loading convention. Any story introducing its own config shape (e.g. `athena-lib-integration` reusing `athena_runner.config.RunConfig`) should either reuse an existing
  upstream config object as-is (as ALI-2 does) or, if a story needs a project-local config of its own, follow `PathConfig`'s frozen-dataclass + `.load(path)` shape rather than inventing ad hoc env-var
  reads — one config pattern across `src/lib/*`, not one per module.
- **2026-10-01 (extended design review — import-cycle / dependency-direction):** `src/lib/*` modules must form a one-directional dependency graph with no cycles — e.g. `athena/` may depend on nothing
  else under `src/lib/`, `auth/` may be depended on by `athena/` (for SSO credential refresh) but must never import `athena/` back, and `report_render/`/`csv_io`/`har/` are leaf modules depended on by
  pipeline/investigation code, not by each other. Whichever story is picked up last under this epic should add a lightweight `tests/lib/test_no_import_cycles.py` (walk `src/lib/`'s module graph,
  assert no back-edges) rather than relying on manual review to catch a future cycle.
- **2026-10-01 (extended design review — shared test-fixture duplication):** six+ stories under this epic each need the same handful of fake/mock collaborators (a fake clock, a fake `boto3` client
  stub, a minimal conforming `Protocol` stub for conformance tests). Introduce `tests/lib/conftest.py` with these as reusable `pytest` fixtures the first time a second story needs one of them (likely
  `auth-lib-migration`, since it depends on `athena-lib-integration`), rather than each story re-defining its own ad hoc version — a DRY violation across test code is still a DRY violation.
- **2026-10-01 (extended design review — packaging / import-path convention):** this repo has no `pyproject.toml`/`setup.py`/`pytest.ini`/`conftest.py` at the repo root; `tests/` imports via `from
  src.lib...` only because `python -m pytest` is invoked from the repo root (per the `Makefile`'s `test` target). This works for `pytest` but is undocumented and will break the first time a non-pytest
  consumer (e.g. a future `investigations/<slug>/scripts/` script) tries `import src.lib.athena` from a different working directory. Flagged here as an open item for whichever story first needs
  cross-directory imports (likely `pipeline-migration`'s first integration task) to either add a root `conftest.py`/minimal `pyproject.toml` with an explicit `src` layout, or document the `python -m
  <module>`-from-repo-root invocation requirement explicitly in that consumer's own `prompt.md`.

## Supersession / coordination

- `functional-code-taxonomy` FCT-1 (module map + replaced-originals citations) and FCT-3 (migration/ownership table) must be updated, when that story is picked up, to cite `athena-mcp-server` as the
  canonical `athena` implementation — not a fifth from-scratch port. This epic does not edit `functional-code-taxonomy`'s files itself (that story is not yet started); it leaves this note as the
  coordination record.
- **2026-10-01:** `docs/archive/flow-correlation-id-logging/` defines the project's FCID (flow-correlation-id) logging convention — `contextvars`-propagated, auto-injected via a `logging.Filter`, no
  manual `fcid` parameter on any adapter method. `athena-lib-integration`'s ALI-2 adapter (and every other module's adapter here) should adopt that convention's log-line shape once implemented. This
  epic does not implement the convention itself; this is the coordination record. **Landed state (2026-10-02, ALI-7):** the minimal FCID-1 slice (`src/lib/logging/context.py` —
  `bind_fcid`/`current_fcid`/`FcidLogFilter`) was built as an ALI-5 prerequisite, since `batch.py`'s `BatchQueryRunner` needed FCID to survive a `ThreadPoolExecutor` boundary; `batch.py` and
  `progressive.py` both attach `FcidLogFilter` to their own module logger and log FCID-tagged lines. `adapter.py` itself does **not** yet attach the filter or log FCID-tagged lines — this remains open
  for whichever story next touches `adapter.py`, since ALI-5/ALI-6 only needed the propagation primitives, not a retrofit of the adapter's own existing log calls. `redact_params` and a project-wide
  `setup_logging()` formatter wiring also remain unimplemented, per `src/lib/logging/context.py`'s own module docstring.
- `athena-lib-integration` must stay reconciled with `athena-mcp-server`'s own `CONTEXT.md` "Known open item" (the `aws-access-cli` sibling-checkout namespace-package merge for
  `tool_config.py::_load_mtn_registry`) — that fragility is upstream of this epic, not introduced by it, but the adapter must not paper over it silently if it resurfaces.

## Epic done when

- **athena-lib-integration** — `athena-mcp-server` is a pinned git submodule; `src/lib/athena/adapter.py` implements FCT-2's `Protocol` by delegating to `athena_runner`, with passing mocked tests; no
  `query_executor`/`aws_clients` logic is duplicated in `ih-trace-lab`.
- **report-render-lib-migration** — `src/lib/report_render/` has a concrete Strategy-per-format writer replacing all cited `github_copilot` originals, with passing tests and a `Protocol` conformance
  pair.
- **har-lib-migration** — `src/lib/har/` has a concrete loader replacing all four cited originals, with passing tests and a `Protocol` conformance pair.
- **auth-lib-migration** — `src/lib/auth/protocols.py` + concrete implementer exist, DIP-injected, with passing tests.
- **csv-io-lib-migration** — `src/lib/csv_io/protocols.py` + concrete implementer exist, DIP-injected, with passing tests.
- **curl-to-python-lib-migration** — `src/lib/curl_to_python/protocols.py` + concrete implementer exist, with passing tests.
- No file under `/Users/abhadra/github_copilot` was created, edited, or deleted by any story in this epic.
