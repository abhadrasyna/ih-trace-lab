# Pre-implementation design review — findings (spec)

> Audit evidence, not a task list — no `- [ ]` checkboxes here, per `docs/plan/README.md`'s "Extra files" convention. `tasks.md` drives the work; this file is what PIR-1/PIR-2/PIR-3 produced and cite.

Severity: **blocking** (will fail a stated task gate as written) · **high** (real SOLID/extensibility gap, fix before coding starts) · **medium** (worth fixing, not urgent) · **low** (nit/consistency
only). Disposition: **autofix** (applied directly in this story, see commit) · **flagged** (judgment call, left for a human — see "Flagged for human decision" below).

## src-lib-migration (6 stories)

| # | Story | Finding | Principle | Severity | Disposition |
|---|---|---|---|---|---|
<!-- lint-ignore-length -->
| 1 | `athena-lib-integration` | `src/lib/athena/protocols.py`'s `AthenaClient` defines `start_query`/`poll_status`/`fetch_results`; `athena-lib-integration/stories.md`'s ALI-2 task text and class diagram name `run_query`/`poll_status`/`download_results` instead. ALI-2's own instruction is "implement that exact `Protocol`, not a new one invented here" — as written, the story cannot satisfy its own gate. | LSP / interface consistency | **blocking** | **autofix** — `athena-lib-integration/stories.md` renamed to match `protocols.py` (the FCT-2-landed, authoritative artifact); `protocols.py` is unchanged. |
<!-- lint-ignore-length -->
| 2 | `athena-lib-integration` | ALI-3's DIP-enforcement test (`test_adapter_constructor_requires_injection`) and `auth-lib-migration`'s AUM-2 DIP-enforcement test (`test_ensure_session_does_not_construct_own_boto3_client`) assert two *different* things under the same "DIP enforcement" banner — one checks construction fails without args, the other checks no internal `boto3` call. Neither module's test suite checks both. Inconsistent application of the same stated principle across stories doing the same job. | DIP (test-level enforcement) | medium | **flagged** — see below; deciding the canonical two-assertion pattern is a design choice, not a doc typo. |
<!-- lint-ignore-length -->
| 3 | `report-render-lib-migration` | RRM-2's class diagram shows a dangling `FutureStrategy` node ("new shape, new implementer, no edit to existing ones") but no selection mechanism is designed — consumers presumably `import CsvReportWriter` directly, coupling every consumer to a concrete class name rather than selecting by a format key. OCP is satisfied for *adding* a writer; it is not obviously satisfied for *consumers choosing* one without an edit at each call site. | OCP / DIP (construction site) | medium | **flagged** — adding a factory/registry now may be premature (only 2 shapes identified by RRM-1); a real 3rd consumer is the natural trigger, per this project's own YAGNI convention. |
<!-- lint-ignore-length -->
| 4 | `curl-to-python-lib-migration` | CPM-1's own task text already concedes: "No specific `github_copilot` original was cited... this module is built ahead of a proven-duplication trigger." This is the one `src-lib-migration` module with no confirmed real consumer at authoring time — every other module cites concrete `github_copilot` originals it replaces. | YAGNI (project-wide stated principle, not strictly SOLID) | high | **flagged** — authorizing speculative build-ahead is a scope decision the epic's own README already made once (2026-09-30); re-confirming it is a human call, not something this review should silently reverse. |
<!-- lint-ignore-length -->
| 5 | `csv-io-lib-migration` | CIM-1 explicitly applies ISP (split reader/writer `Protocol`s) — the one module in this set that states and applies an ISP trigger. No finding; cited as a **positive pattern** other modules' future `Protocol` growth should match once a `Protocol` approaches 3+ methods serving different consumer subsets. | ISP | n/a | n/a (positive, no action) |
<!-- lint-ignore-length -->
| 6 | `har-lib-migration` | HLM-2 explicitly requires a specific exception type on malformed input ("fail loudly, no silently-wrong partial results") — matches this project's own global convention. No finding; cited as a **positive pattern**. | SRP / fail-loudly convention | n/a | n/a (positive, no action) |
<!-- lint-ignore-length -->
| 7 | all 6 stories | Every module's last task is a `CONTEXT.md`-pointer-only commit *and* a `docs/plan/src-lib-migration/README.md` status-row update in the same task — these are two different files with two different purposes (global state snapshot vs. this epic's own progress view) bundled into one task line with one commit message. Minor process nit, not a code/design defect. | SRP (applied to task-authoring itself) | low | **flagged** — splitting into two tasks per module (×6) adds six more task-table rows for a cosmetic gain; worth a human call on whether it's worth the churn. |

## pipeline-migration (2 stories)

| # | Story | Finding | Principle | Severity | Disposition |
|---|---|---|---|---|---|
<!-- lint-ignore-length -->
| 8 | `aws-access-cli-pipeline-migration` | AAM-2's thin-wrapper pattern (CLI parsing + business-logic call + `report_render` call, no logic in the wrapper) is applied consistently across all 15 `run_*.py` scripts per the task text. **Positive pattern** — this is the cleanest SRP application in either plan; a good reference for how `ctap-smvod`'s `run_pipeline.py` orchestrator (CSM-2) should eventually look once its 6 steps are each thin. | SRP | n/a | n/a (positive, no action) |
<!-- lint-ignore-length -->
| 9 | `ctap-smvod-investigation-migration` | CSM-2's `run_pipeline.py` class diagram models all 6 steps as methods on one `RunPipeline` class. Unlike AAM's per-report thin-wrapper split, this keeps step4/step5 ("merge_session_debug", "analyze") as methods on the orchestrator itself rather than delegating to the already-identified `merge_*.py`/`analyze_*.py` business-logic scripts named in CSM-1's own audit. Risk: the orchestrator could accumulate business logic inline instead of staying a thin coordinator, the same anti-pattern `functional-code-taxonomy`'s own motivating example (the "1000+ LOC strategy file") warns against. | SRP | high | **flagged** — CSM-2's task text does say scripts are "ported... business-logic scripts," so the diagram may just be an abbreviated illustration, not the literal intended class shape; a human implementing CSM-2 should confirm the diagram is illustrative before coding, not treat it as the literal target class design. |
<!-- lint-ignore-length -->
| 10 | both stories | Neither story's Athena-pull step (AAM's `adoption.py`, CSM-2/CSM-4) designs for batched/concurrent query submission or a SQL-fingerprint result cache — both submit one query, poll, fetch, sequentially, per call site. Matches the gap already flagged in the 2026-10-01 conversation before this story existed. | Performance / extensibility (not strictly SOLID) | medium | **flagged** — this is `athena-lib-integration`'s adapter-level design gap, inherited by both pipeline consumers; fixing it once at the adapter benefits both stories without editing either. |

## reference-code-gap-migration (10 sub-stories)

None of the 10 sub-stories have concrete design yet — each currently defines only one audit-only first task (`<PREFIX>-1`, e.g. `APL-1`, `VTP-1`), confirmed by spot-checking
`applause-investigation-migration/tasks.md` and `vod-playback-timing-probe-tool-migration/tasks.md`. There is no class diagram, `Protocol`, or adapter design to critique line-by-line yet — that only
appears once each sub-story's 2nd+ task is written, which this epic's own convention deliberately defers.

| # | Scope | Finding | Principle | Severity | Disposition |
|---|---|---|---|---|---|
<!-- lint-ignore-length -->
| 11 | all 10 sub-stories | `src-lib-migration`'s own README states a cross-cutting discipline: "Diagrams are authored now, at design time, not deferred to the implementing session" (class + sequence Mermaid per story, in that story's own `stories.md`). `reference-code-gap-migration/README.md`'s "Cross-cutting constraints" section has no equivalent line — nothing requires the same discipline once each sub-story's 2nd task gets written. Without it, there is a real risk 10 sub-stories each invent their own documentation shape instead of mirroring the other two plans' already-proven convention. | Consistency / extensibility of the planning process itself | high | **reverted 2026-10-01** — this was a self-introduced extension outside the requester's stated review criteria (SOLID, Python clean code, Athena optimization, FCID logging, extensibility); the line added to `reference-code-gap-migration/README.md`'s "Cross-cutting constraints" was removed at the requester's explicit instruction. Left here only as a record that it was considered and deliberately not kept. |

## Flagged for human decision

Self-contained — each item below states the decision needed and the file it would touch, without requiring a re-read of this session's transcript.

**All 6 items below were resolved on 2026-10-01, in a follow-up session; each note states the decision made and where it landed.**

1. **Finding #2 (DIP test pattern)** — **Resolved: standardize now.** `src-lib-migration/README.md`'s "Cross-cutting constraints" gained the canonical two-assertion pattern (construction-without-
   collaborators raises + no direct real-client call inside the adapter). `athena-lib-integration/stories.md`'s ALI-3 and `auth-lib-migration/stories.md`'s AUM-3 both now list the missing half of the
   pair explicitly.
2. **Finding #3 (report_render factory)** — **Resolved: build now** (the requester overrode this review's "defer" recommendation). `report-render-lib-migration` gained a new `RRM-3` task
   (`src/lib/report_render/factory.py`, a Factory Method keyed by shape) between the prior RRM-2 and RRM-3; the prior RRM-3/RRM-4 renumbered to RRM-4/RRM-5. `prompt.md`/`tasks.md`/`stories.md` all
   updated to match.
3. **Finding #4 (curl_to_python YAGNI)** — **Resolved: real consumer confirmed, not a hard gate.** The requester clarified the actual trigger: a HAR-driven manual timing/latency investigation workflow
   (analyst copies a single request's curl command identified via HAR inspection, converts it, re-runs for timing measurement). `curl-to-python-lib-migration/prompt.md` and CPM-1's spec in
   `stories.md`/`tasks.md` were corrected to cite this scenario instead of the prior "no citation found, built speculatively" framing.
4. **Finding #7 (task-authoring SRP nit)** — **Resolved: leave bundled, no split.** The requester chose not to split the `CONTEXT.md` + epic-README task across the 6 `*-lib-migration` stories; no file
   changes made for this item.
5. **Finding #9 (ctap-smvod orchestrator shape)** — **Resolved: diagram was literal, now fixed.** `pipeline-migration/ctap-smvod-investigation-migration/stories.md`'s CSM-2 class diagram now shows
   `RunPipeline` delegating to explicit `MergeScript`/`AnalyzeScript` collaborators (mirroring `merge_*.py`/`analyze_*.py`) instead of modeling their logic as inline methods, with a dated note
   explaining the fix.
6. **Finding #10 (Athena batch/cache design)** — **Resolved: scoped and added as new tasks.** Follow-up scoping (small batches of 2-5 independent queries; TTL-based result caching; existing
   `athena_runner` batch support unknown) produced two new tasks in `athena-lib-integration`: `ALI-4` (audit whether `athena_runner` already supports batching/caching) and `ALI-5`
   (`src/lib/athena/batch.py` + `cache.py` — bounded-concurrency `BatchQueryRunner` + `InMemoryTtlCache`, both DIP-compliant). The prior ALI-4 (doc pointers) renumbered to `ALI-6`.

## Extended review, 2026-10-01 (same day, follow-up pass)

The requester asked for the review to go beyond their originally-stated criteria (SOLID, Athena optimization, FCID logging, extensibility) to catch anything else at-risk before implementation starts,
explicitly to avoid refactoring multiple times. Scope was agreed via `ask_user`: all 8 proposed dimensions below, full depth, plus a 9th requirement the requester specified directly.

**A concrete, already-committed defect was found first** (not a hypothetical): `athena-lib-integration`'s ALI-5 batch design (added in the 6-item resolution above) did not implement
`flow-correlation-id-logging/stories.md`'s own stated `contextvars`/`ThreadPoolExecutor` caveat — FCID would have silently vanished from log lines inside batch worker threads. Fixed as a new ALI-5
implementation point (capture `copy_context()` on the calling thread, submit work through it).

1. **Exception hierarchy** — `athena-lib-integration`'s ALI-2 gained `src/lib/athena/exceptions.py` (mirrors, never leaks, `athena_runner.exceptions.*`); `src-lib-migration/README.md` gained a
   generalized cross-cutting rule requiring the same pattern in every other `src/lib/*` module.
2. **AWS throttling retry/backoff** — confirmed missing in `athena_runner.query_executor.py` by direct source read; added to ALI-2 as an adapter-layer responsibility (exponential backoff + jitter,
   scoped to throttling-class `ClientError`s only).
3. **Credential/session reuse under concurrency** — `athena_runner.aws_clients.AwsClientFactory` builds boto3 clients from one shared `boto3.Session` per call, with no documented concurrent-call
   safety; ALI-5 now requires all `AthenaClient` instances to be constructed sequentially before its thread pool starts, never inside a worker thread.
4. **PII/secrets in logs** — `flow-correlation-id-logging/stories.md`'s log-line shape spec gained a redaction rule: log `sql_fingerprint` (a short hash) instead of raw SQL text, and only allow-listed
   param keys, never an opaque param dump.
5. **Config management consistency** — confirmed `src/lib/paths/config.py`'s `PathConfig` (frozen dataclass + `.load(path)`) as the project's existing config pattern; ALI-2 now reuses
   `athena_runner.config.RunConfig` directly instead of inventing a new shape, and `src-lib-migration/README.md` gained a generalized rule for other modules to follow the same precedent.
6. **Import-cycle / dependency-graph check** — `src-lib-migration/README.md` gained an explicit one-directional dependency rule for `src/lib/*` (e.g. `athena/` depends on nothing else under
   `src/lib/`), with a future `tests/lib/test_no_import_cycles.py` flagged for whichever story is picked up last.
7. **Test-fixture duplication (DRY in tests)** — `src-lib-migration/README.md` flagged a future shared `tests/lib/conftest.py` for fake collaborators reused across 6+ stories, to be introduced the
   first time a second story needs one.
8. **Packaging/import-path consistency** — confirmed no `pyproject.toml`/`setup.py`/`conftest.py` exists at the repo root; `tests/` only imports `from src.lib...` successfully because of `python -m
   pytest` invoked from repo root. Flagged as an open item in `src-lib-migration/README.md` for whichever story first needs cross-directory imports (likely `pipeline-migration`'s first integration
   task).
9. **Progressive/incremental Athena query scoping (requester-specified)** — `athena-lib-integration` gained a new `ALI-6` task, `src/lib/athena/progressive.py`: a `ProgressiveQueryRunner` that runs a
   query against a narrow scope first, widens only when a `SufficiencyCheck` says the result isn't enough, stops when a `ScopeSequence` is exhausted, and combines rows across every scope actually run
   (never dropping an earlier scope's rows). The prior ALI-6 (doc pointers) renumbered to `ALI-7`.

All of the above were written directly into the affected stories'/epics' own files (`athena-lib-integration/stories.md`, `tasks.md`, `prompt.md`; `flow-correlation-id-logging/stories.md`;
`src-lib-migration/README.md`) rather than only recorded here — this section is the audit trail, not the source of truth for the resulting design.
