# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `docs/refactor/` — a generic (Python-scoped) refactor playbook (`README.md` index + `design-principles.md`, `code-deduplication-and-taxonomy.md`, `planning-protocol.md`,
  `logging-and-correlation-id.md`, `process-discipline.md`, `python-hygiene-and-automation.md`, `architecture-diagrams.md`, `code-review-checklist.md`) distilling this repo's own `docs/archive/`,
  `docs/plan/`, and `PYTHON_DESIGN.md` history into a reusable method for refactoring a different ad hoc Python legacy tree later. No project-specific names (entities, tenants, repos) appear in it by
  design — it is meant to be read by a future, unrelated Python project.
- `.github/hooks/session-context.json` — a native Copilot CLI `sessionStart` hook (not a git hook) that auto-injects a short reminder into every new/resumed session: read `CONTEXT.md`, state
  `CONTEXT.md ✓`, confirm scope when files aren't named, and state a plan + wait for go-ahead before non-trivial changes. Added to cut the highest-recurrence rows in `suggestions.md`
  (`wait-for-explicit-go-ahead-before-editing`, `state-context-md-checkmark-explicitly`, etc.) at the source instead of only catching them after the fact in `session-close`. Injects a short pointer,
  not the full `AGENTS.md`/`CONTEXT.md` text, to avoid adding token cost every session.
- `AUTOMATION.md` (root) + `.github/hooks/autopilot-checkpoint.json` / `scripts/dev/hooks/autopilot_checkpoint.py` — diagnosed from the `src-lib-migration` epic's 2026-10-02 run, which executed all 24
  task segments inside one single-agent session with no re-check between segments (the direct cause of `suggestions.md`'s `re-read-context-on-resumed-task-segments` and repeated
  `state-plan-before-editing`/`wait-for-explicit-go-ahead-before-editing` rows). `AUTOMATION.md` is the how-to for running a multi-story epic via one sub-agent per story instead (token cost scales
  with story count, not story count squared, and each sub-agent's own first turn satisfies Steps 1-3 fresh). `autopilot_checkpoint.py` is the fallback for when sub-agent delegation genuinely isn't
  available: an `agentStop` hook that forces a plan/go-ahead checkpoint every 5 turns regardless of commits, complementing (not replacing) `session_close_on_commit.py` (commit-triggered) and
  `session-context.json` (`sessionStart`-triggered only).
- **Copilot Memory is enabled** (`/memory on`, confirmed 2026-10-01) — a per-user CLI account setting, not a repo file; there is nothing under this repo to look for. Intended to reduce the
  `avoid-broad-filesystem-finds`/`avoid-mid-session-rereads` rows in `suggestions.md` by letting the CLI recall repo-structure facts across sessions instead of re-discovering them each time.
- `docs/archive/tenant-registry/` — story complete: `config/tenants.yaml` is now the canonical MTN tenant-identifier config for all 4 confirmed opcos (Go ID, Matisse Project/Client Tenant ID, Athena
  Tenant ID, Lightstep project/region, shared-project disambiguation attribute); `src/tenant_registry/` loads it and resolves per-system query contexts (`TenantRegistry`/`QueryTarget`); this assistant
  must consult it (via `scripts/resolve_tenant.py` or the loader directly) before any Lightstep/Matisse/Athena MCP call, per `docs/guides/tenant-resolution.md`'s CLI-first protocol. TR-1's scratch
  probe was confirmed against real, human-reviewed Lightstep MCP data (dedicated SA project + shared Ghana project disambiguated by `busUnitId`) before any production code was written.
- `docs/archive/query-catalog/` — story complete: `queries/athena/` + `queries/lightstep/` now provide a deduplicated, parameterized-template query catalog harvested from `github_copilot`'s 3
  `QUERY_CATALOG.md` files plus `lightstep-query-templates.md`; the Athena/Lightstep harvest scripts are in `scripts/dev/`, the query indexes/templates live under `queries/`, the query workflow guide
  lives at `docs/guides/query-catalog.md`, and the ported (not yet run) Athena DDL-cache tooling plus `knowledge/README.md` live under `knowledge/` / `scripts/athena/`.
- `docs/archive/project-taxonomy/` — story complete: `docs/guides/project-taxonomy.md` now defines the four categories, folder skeletons, prior-art checklist, pipeline cron-cutover procedure, and PT-7
  data/knowledge conventions; `config/data_paths.yaml` is the path-template source of truth; `scripts/dev/check_project_taxonomy.py` audits unclassified top-level dirs; and
  `.github/skills/investigation-doc-sync/SKILL.md` defines the deferred cross-session case-doc sync workflow. `structure.md` remains the canonical target-tree reference for this story and
  `functional-code-taxonomy`.
- `docs/archive/functional-code-taxonomy/` — story complete: `docs/guides/functional-code-taxonomy.md` now maps the six shared `src/lib/*` modules, states the shared-vs-specific test, records the
  `query-catalog` boundary, and documents the delegated cross-project duplicate-check. `src/lib/{athena,report_render,har}/protocols.py` and `src/lib/paths/{protocols.py,config.py}` now provide the
  shared Protocol/path-resolution seams, with tests; `scripts/dev/generate_code_registry.py` inventories reusable code outside `scratch/`. Sibling to `project-taxonomy` (categories vs. shared code)
  and `query-catalog` (SQL text vs. execution code).
- `docs/archive/scratch-script-registry/` — story complete: root `SCRIPTS.md` is now generated from the live `scripts/` + `scratch/` tree via `scripts/dev/generate_scripts_registry.py`;
  `scripts/dev/promote_scratch_scripts.py` provides manual promotion with registry refresh; `scratch/SCRATCH.md`, `AGENTS.md`, and the repo-local `.github/skills/session-close/SKILL.md` enforce the
  delegated duplicate-check and close-out regeneration workflow; `tests/dev/` covers both CLIs.
- `docs/archive/reference-knowledge-harvest/` — story complete through RKH-17: `knowledge/` now contains the harvested VOD asset mapping/pipeline references, MTN SA Lightstep tag/query references,
  Applause Athena/CSV gotchas, adoption playback-outcome gap notes, CTAP-SM-VOD playback/CDN methodology docs, MTN/TIM Play tenant+DRM references, the 3 root knowledge ports, and the SRE Jira project
  reference. The story remains extensible — future `github_copilot/*` folders would reopen it by appending new `RKH-N` tasks rather than creating a new story.
- Story-archiving is now scripted and self-triggering: `scripts/dev/archive_completed_story.py <slug>` (epic-aware; refuses incomplete slugs) does the `git mv` + cross-reference rewrite + 200-char
  reflow described in `docs/plan/README.md`'s "Archiving a completed story" section and stages the result for review/commit; the non-blocking `story-archive-check` pre-commit hook
  (`scripts/dev/hooks/check_unarchived_stories.py`) warns when a story looks complete but hasn't been archived yet. Separately, `.github/hooks/session-close-trigger.json` (native Copilot CLI
  `sessionStart`/`agentStop` hooks, backed by `scripts/dev/hooks/session_close_on_commit.py`) detects when `HEAD` moved during a turn (i.e. a commit just landed) and forces one more turn whose prompt
  asks the agent to invoke the `session-close` skill immediately, instead of relying on the end of the whole session to remember to do it.
- `docs/archive/src-lib-migration/` — epic: real, tested implementations of `functional-code-taxonomy`'s six `src/lib/*` modules (`auth`, `athena`, `csv_io`, `report_render`, `har`, `curl_to_python`),
  ported/refactored from `github_copilot` (read-only reference), one story per module. `athena-lib-integration` is the exception — it wires in `/Users/abhadra/myWork/myOffice/athena-mcp-server` (an
  already-independent, tested repo with the shared `athena_runner` execution stack) as a git submodule and adapts to it, rather than re-porting a fifth copy of that logic.
  `auth`/`csv_io`/`curl_to_python` additionally define their own `Protocol`s here, deferred by `functional-code-taxonomy` FCT-2. `athena-lib-integration` is complete through ALI-6 (ALI-7 is
  docs-only); see `docs/archive/src-lib-migration/README.md`'s Stories table for the other five stories' status and first unchecked task.
- `vendor/athena-mcp-server` — pinned git submodule (see `docs/guides/submodules.md` for init/update steps; `git submodule update --init` after cloning, plus `pip install -e vendor/athena-mcp-server`
  since the submodule's `athena_runner` package isn't on PyPI). `src/lib/athena/adapter.py` is a thin DIP adapter delegating to it — no `query_executor`/`aws_clients` execution logic is duplicated in
  `ih-trace-lab` itself; `src/lib/athena/exceptions.py` defines this module's own exception hierarchy so callers never need to catch `athena_runner.exceptions.*` or raw
  `botocore.exceptions.ClientError` directly.
- `src/lib/athena/batch.py` + `cache.py` — bounded-concurrency batch submission (`BatchQueryRunner`, pool size from `athena_runner.config.RunConfig.max_concurrency`) with a fingerprint-keyed TTL
  result cache (`InMemoryTtlCache`), for consumers submitting multiple independent queries at once (e.g. per-tenant/per-day fan-out). One query's failure never blanks out the batch's other results
  (`AthenaBatchExecutionError` carries both partial results and failures).
- `src/lib/athena/progressive.py` — progressive scope-widening query runner (`ProgressiveQueryRunner`): runs a narrow scope first, widens only if a consumer-supplied `SufficiencyCheck` says the result
  isn't enough, stops when the consumer's `ScopeSequence` is exhausted (or a `max_rounds` backstop is hit, guarding against a misbehaving collaborator pair), and combines rows across every scope
  actually run.
- `src/lib/report_render/writers.py` + `factory.py` — Strategy-based report writers (`MarkdownTableWriter`, `CategoryBreakdownWriter`, `StatisticalWriteupWriter`), selected via a Factory Method
  (`make_report_writer(shape)`) keyed by shape (`"markdown_table"`/`"category_breakdown"`/`"statistical_writeup"`), replacing the 8+ duplicated `github_copilot` originals cited in
  `report-render-lib-migration/stories.md`'s RRM-1 audit. Future consumers call `make_report_writer(shape)`; none import a concrete writer class directly.
- `src/lib/har/loader.py` — `JsonHarEntryLoader` implements `HarEntryLoader` (`functional-code-taxonomy` FCT-2's `Protocol`), replacing the 4 duplicated `github_copilot` HAR `log.entries` loaders
  cited in `har-lib-migration/stories.md`'s HLM-1 audit (`applauseInvestigation/scripts/analyze_har.py::iter_entries()`,
  `vod-playback-timing-probe/scripts/{extract_content_ids_from_har.py,summarize_har_playbacks.py}::_load_entries()`, `vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()`).
  Accepts `str | Path | an open file handle`; `load_json_entries()`'s JSON-filter/response-parse step stays out of scope as project-specific logic for a future consumer.
- `src/lib/auth/protocols.py` + `sso.py` — `AuthProtocol` (`ensure_session`/`refresh_if_expired`), generalized from `athena_runner.sso_auth.SsoCredentialRefresher`'s proven shape, and its concrete
  `SsoAuth` implementer. `SsoAuth` is constructor-injected with `refresher_factory`/`session_factory` collaborator callables (rather than one bound collaborator) because the real
  `SsoCredentialRefresher` binds a single profile per instance while `AuthProtocol`'s methods take `profile_name` per call; it never builds its own `boto3` object or reimplements the SSO refresh
  polling loop.
- `src/lib/csv_io/protocols.py` + `csv_file.py` — split `CsvReaderProtocol`/`CsvWriterProtocol` (ISP) plus stdlib-backed `CsvFileReader`/`CsvFileWriter` for raw CSV I/O, distinct from
  `report_render`'s formatted-output Strategy (`csv_io` owns getting rows in/out of files; `report_render` renders already-read/normalized rows). Matches `csv.DictReader`/`csv.DictWriter` defaults
  exactly, per `csv-io-lib-migration/stories.md` CIM-1's requester-approved file-boundary audit.
- `src/lib/curl_to_python/protocols.py` + `converter.py` — `CurlConverterProtocol` (`convert(curl_command) -> str`) and its concrete `CurlToRequestsConverter`, built ahead of a proven-duplication
  trigger per this epic's explicit authorization (no existing `github_copilot` file was found to replace — see `curl-to-python-lib-migration/stories.md`'s CPM-1 finding). Parses curl's
  method/URL/headers/data grammar only (any other flag/quoting form raises `UnsupportedCurlFlagError` by name rather than producing silently-wrong output) and renders Python `requests.request(...)`
  source text; never executes the converted request.
- `src/lib/logging/context.py` — minimal FCID (flow-correlation-id) `contextvars` propagation slice (`bind_fcid`/`current_fcid`/`FcidLogFilter`), built as an `athena-lib-integration` ALI-5
  prerequisite so FCID survives a `ThreadPoolExecutor` boundary. `docs/plan/logging-framework/` has now started implementing the rest of FCID-1's deferred runtime wiring around it:
  `src/lib/logging/bootstrap.py` mints/binds one FCID per entry point, `src/lib/logging/setup.py` injects `%(fcid)s` on every handler, and `src/lib/logging/redact.py` provides allow-list-based
  parameter masking.
- `docs/plan/logging-framework/` — story (open; LFR-1 done, LFR-2..5 remaining): closes the deferred FCID/runtime gap flagged by both `src/lib/logging/context.py` and `pipeline-migration`'s README.
  LFR-1 is complete: `init_logging()` now composes `setup_logging()` + FCID binding, `setup_logging()` auto-injects `fcid` into every record via handler filters, and `redact_params()` implements the
  FCID-1 allow-list masking rule. Remaining tasks define/apply the minimum logging contract, wire the bootstrap into `aws_access_cli` entry points, make the contract binding in
  `code-review-checklist.md`, and add coordination notes for still-unretrofitted consumers. `investigations/ctap-smvod/` and other consumers are explicitly deferred (LFR-5 coordination notes only),
  not retrofitted here.
- `src/lib/logging/setup.py` — the canonical `setup_logging()` entrypoint (moved here from `logs/setup_logging.py` so code and its own generated runtime artifact, `logs/app.log`, aren't colocated in
  one directory). Resolves its log directory from a new `logs_root` key in `config/data_paths.yaml` (default `logs`) instead of a hardcoded path relative to the module file, consistent with the
  project's single-config-loading-convention guidance; `logs/` itself still holds the generated `app.log` and its `.gitignore`. All 4 prior `logs.setup_logging` import sites were updated to
  `src.lib.logging.setup`.
- `docs/plan/pipeline-migration/` — epic: ports `aws-access-cli` (→ `src/pipelines/aws_access_cli/`, importable package name, external slug stays `aws-access-cli`; pipeline category) and
  `ctap-smvod-session-report` (→ `investigations/ctap-smvod/`, recurring-campaign category, incl. manual-Lightstep-step relocation) from `github_copilot` (read-only reference), replacing their
  duplicated executor/auth/SQL/output logic with `src/lib/*`, `query-catalog`, and `project-taxonomy` PT-7's ISO-prefix path convention respectively. Both stories ran in parallel in isolated git
  worktrees (2026-10-03). `ctap-smvod-investigation-migration` is **done** (CSM-1..7, 57 tests passing); `aws-access-cli-pipeline-migration` is implemented through AAM-4 and AAM-6 (25 tests passing),
  with AAM-5 (PT-6 cron-cutover for the 3 live crontab entries) left open — `Owner: human (crontab access required)`, operator runbook in that story's own `session-log.md`.
- `docs/plan/reference-code-gap-migration/` — **epic** (promoted from a single story by its own GAP-1 task, 2026-09-30): ports the 10 `github_copilot` projects (~166 Python files) that neither
  `pipeline-migration` nor `src-lib-migration` cover, into 10 sub-stories tiered by effort/blocking (`README.md`'s decision log) — Tier 1 cheap (`applause-investigation-migration`,
  `astro-events-household-investigation-migration`, `shaka-6001-sa-investigation-migration`, `root-scripts-tool-migration`), Tier 2 medium (`vod-asset-ingestion-investigation-migration`,
  `mtn-zm-device-investigation-migration`, `mtn-network-traffic-tool-migration`, `root-investigations-migration`), Tier 3 blocked on two newly-promoted `src/lib/*` modules
  (`vod-playback-timing-probe-tool-migration` needs `mpd`, `smarttv-mtntv-tool-migration` needs `crypto_signing` — both modules to be built by `src-lib-migration`, not this epic). GAP-1 also flagged a
  correction to `project-taxonomy/structure.md`/`stories.md`: `vod-asset-ingestion-mapping` recategorized from `experiments/` to `investigations/vod-asset-ingestion/` (recurring campaign, per its own
  README); a second, similar tension for `vod-playback-timing-probe` (audit suggests "tool", `structure.md` still examples it under `experiments/`) was flagged but deliberately left unresolved for a
  future `project-taxonomy` session. `oasis-athena-mcp` was checked and confirmed not a gap (superseded by the `athena-mcp-server` submodule). Root `prompt.md` is now a pure router (no session-start
  protocol of its own) — each of the 10 sub-stories has its own `prompt.md`/`tasks.md`/`stories.md` and first unchecked task (all currently their own `<PREFIX>-1` audit task). Not yet implemented
  beyond GAP-1 — see `README.md`'s Stories table for which sub-story to pick up next. **2026-10-01:** cross-cutting constraint added requiring any sub-story that ports a CSV/report-writing script to
  adopt `PathResolver`'s naming helpers (`format_snapshot_filename`/`format_range_filename`/`format_rollup_filename`), not just its directory resolver — confirmed by source read that
  `shaka-6001-sa-error-analysis`, `mtn-zm-session-device-investigation`, `astro-events-household-report`, and `vod-playback-timing-probe` each still hardcode their own ad hoc output-path logic today;
  mirrors `pipeline-migration` AAM-4's already-designed task shape.

- `docs/archive/reference-folder-diagrams/` — story complete: `scripts/reference_diagram/` now supports per-project internal-import flowcharts, and `docs/reference-diagrams/` now indexes 12
  folder-level Mermaid pages (generated flowcharts plus hand-authored convergence/orchestration/state diagrams) covering every in-scope `github_copilot` migration folder except deliberately-excluded
  `oasis-athena-mcp`; the set makes `reference-code-gap-migration`'s tiering and its `src/lib/mpd/` / `src/lib/crypto_signing/` promotion decisions visible, not just prose.
- `docs/archive/flow-correlation-id-logging/` — story complete (design-only): defines the project's FCID (flow-correlation-id) convention — one id per run, minted once at each consumer's entry point,
  propagated via a `contextvars.ContextVar` (no manual parameter-threading through `src/lib/*` adapter methods), auto-injected into every log line via a `logging.Filter`. `stories.md` carries a
  sequence diagram (one Athena query inside one pipeline run) and a component diagram (FCID flowing through `src/lib/*` into all three migration epics' consumers); no `src/lib/logging/` module or code
  exists yet — that is deferred to a follow-up story once a real consumer (first candidate: `athena-lib-integration` ALI-2) needs it. Coordination notes were added to `src-lib-migration`,
  `pipeline-migration`, and `reference-code-gap-migration`'s `README.md`s pointing here. Cross-process FCID propagation (subprocess/cron boundaries) is explicitly out of scope, left open for later.
- `docs/archive/pre-implementation-design-review/` — story complete: a SOLID/clean-code/extensibility design review of all 18 not-yet-started stories across `src-lib-migration`, `pipeline-migration`,
  and `reference-code-gap-migration`, run before any of them starts producing code. `spec.md` is the full findings table. One low-risk finding was fixed directly: a blocking method-name/signature
  mismatch between `src/lib/athena/protocols.py`'s `AthenaClient` and `athena-lib-integration/stories.md`'s own ALI-2 class diagram, which would have failed that story's own task gate. A second
  finding (a design-time-diagram-discipline parity constraint for `reference-code-gap-migration/README.md`) was applied, then reverted 2026-10-01 at the requester's instruction as a self-introduced
  extension outside their stated review criteria — `spec.md`'s finding #11 row records this. **2026-10-01 follow-up: all 6 originally-flagged judgment calls resolved** (`spec.md`'s "Flagged for human
  decision" section now records each resolution) — (a) `src-lib-migration/README.md` gained a standardized two-assertion DIP-enforcement test pattern, applied to `athena-lib-integration`'s ALI-3 and
  `auth-lib-migration`'s AUM-3; (b) `report-render-lib-migration` gained a new `RRM-3` Factory Method task (`src/lib/report_render/factory.py`) selecting a writer by shape key, renumbering the prior
  RRM-3/RRM-4 to RRM-4/RRM-5; (c) `curl-to-python-lib-migration`'s CPM-1 framing corrected to cite its real confirmed consumer (a HAR-driven manual timing/latency investigation workflow), replacing
  the prior "no-citation/speculative" framing; (d) the task-authoring SRP nit (finding #7) was left as-is, no split; (e) `ctap-smvod-investigation-migration`'s CSM-2 class diagram fixed to show
  `RunPipeline` delegating to explicit `MergeScript`/`AnalyzeScript` collaborators instead of modeling their logic as inline methods; (f) `athena-lib-integration` gained two new tasks, `ALI-4` (audit
  existing `athena_runner` batch/cache support) and `ALI-5` (`src/lib/athena/batch.py` + `cache.py` — bounded-concurrency `BatchQueryRunner` + `InMemoryTtlCache`, both DIP-compliant), with the prior
  ALI-4 (doc pointers) renumbered to `ALI-6`. **2026-10-01, same-day extended review pass (user-requested, 8 dimensions + progressive query scoping):** grounded in a direct read of the
  `athena-mcp-server` submodule's source (not speculation) — found and fixed a real defect: ALI-5's just-committed batch design did not satisfy `flow-correlation-id-logging`'s own stated
  `contextvars`/`ThreadPoolExecutor` caveat (FCID would have silently vanished inside worker threads); ALI-5 now captures `copy_context()` on the calling thread before submitting work. ALI-2 gained a
  mirrored `src/lib/athena/exceptions.py` hierarchy (never leaking `athena_runner.exceptions.*`) and throttling retry/backoff (confirmed missing upstream in `query_executor.py`); ALI-5 now reuses
  `athena_runner.config.RunConfig.max_concurrency` (confirmed reserved-but-unconsumed upstream) instead of a redundant new constructor arg, and pre-builds all `AthenaClient` instances sequentially
  before starting its thread pool (`AwsClientFactory`'s shared-`boto3.Session` construction is not documented safe for concurrent calls). A new `ALI-6` task (`src/lib/athena/progressive.py`) adds a
  progressive scope-widening query runner — narrow scope first, widen only if insufficient, combine rows across every scope actually run — per the user's own 9th review requirement; the prior ALI-6
  (doc pointers) renumbered to `ALI-7`. `flow-correlation-id-logging/stories.md` gained a PII/secrets redaction rule (log `sql_fingerprint`, not raw SQL; allow-list param keys).
  `src-lib-migration/README.md`'s cross-cutting constraints gained 5 generalized rules beyond the `athena`-specific instances: exception-hierarchy-per-module, config-loading consistency (cite
  `src/lib/paths/config.py`'s `PathConfig`), import-cycle/dependency-direction (one-directional `src/lib/*` graph, future `test_no_import_cycles.py`), shared test-fixture dedup (future
  `tests/lib/conftest.py`), and the packaging/import-path gap (no root `pyproject.toml`/`conftest.py` yet — `python -m pytest`-from-repo-root is the only reason `from src.lib...` imports currently
  work; flagged as an open item for `pipeline-migration`'s first integration task).
- `ruff.toml` (root) — added 2026-10-03 after `make lint` surfaced 72 errors across 7 unrelated rule families (`DTZ007`, `EXE001`, `PLW1510`, `PIE810`, `G201`, `PYI018`, `TRY401`); root had no ruff
  config at all, so `ruff check` was silently defaulting to its full broad rule set rather than an intentional selection. Curated `select` to `E4`/`E7`/`E9` (core pycodestyle errors), `F` (pyflakes),
  `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM` (flake8-simplify), `C4` (comprehensions) — this is a lint-rule-selection gap only, separate from the still-open
  pytest-import-path/root-`pyproject.toml` gap noted above. An earlier `ruff check --fix` pass (run before this file existed) had also auto-unquoted `src/lib/auth/sso.py`'s `ensure_session(...) ->
  "boto3.Session"` annotation (UP037), which broke `test_ensure_session_does_not_construct_own_boto3_client` (an AST-based test enforcing SsoAuth never references `boto3` directly); re-quoted with `#
  noqa: UP037` and a pointer to the guarding test so future `--fix` runs don't regress it again.

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- `/Users/abhadra/github_copilot` is read-only reference (see `README.md`'s mission statement) — never create, edit, or delete anything there from this project; treat it as prior art to learn the
  "profile of work" from, not a shared codebase.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
