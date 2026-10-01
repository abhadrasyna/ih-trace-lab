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
| 11 | all 10 sub-stories | `src-lib-migration`'s own README states a cross-cutting discipline: "Diagrams are authored now, at design time, not deferred to the implementing session" (class + sequence Mermaid per story, in that story's own `stories.md`). `reference-code-gap-migration/README.md`'s "Cross-cutting constraints" section has no equivalent line — nothing requires the same discipline once each sub-story's 2nd task gets written. Without it, there is a real risk 10 sub-stories each invent their own documentation shape instead of mirroring the other two plans' already-proven convention. | Consistency / extensibility of the planning process itself | high | **autofix** — one line added to `reference-code-gap-migration/README.md`'s "Cross-cutting constraints" requiring the same design-time-diagram discipline for every sub-story's 2nd+ task. |

## Flagged for human decision

Self-contained — each item below states the decision needed and the file it would touch, without requiring a re-read of this session's transcript.

1. **Finding #2 (DIP test pattern)** — decide and document, in `src-lib-migration/README.md`'s "Cross-cutting constraints," one canonical two-assertion DIP-enforcement test pattern (e.g. "every
   adapter test suite asserts (a) construction without required collaborators raises, and (b) no direct call to the real external client/library inside the adapter") that every module's
   `*-lib-migration` story adopts identically, rather than each inventing its own single assertion.
2. **Finding #3 (report_render factory)** — decide whether `report-render-lib-migration` needs a format-selection factory/registry now (adds a seam before a 3rd consumer exists) or waits for RRM-1's
   grouped-list count to actually reach 3+ shapes (pure YAGNI). No file changes until decided.
3. **Finding #4 (curl_to_python YAGNI)** — re-confirm `curl-to-python-lib-migration` still has epic-requester authorization to build ahead of a proven consumer, or make CPM-1's audit the hard gate (do
   not proceed past CPM-1 without a confirmed citation). Touches `src-lib-migration/athena-lib-integration/../curl-to-python-lib-migration/prompt.md`'s scope guard if reversed.
4. **Finding #7 (task-authoring SRP nit)** — decide whether the 6 `*-lib-migration` stories' final `CONTEXT.md` + epic-README task should split into two tasks each (×6 new rows) or stay bundled as a
   pragmatic exception to the SRP-on-tasks idea. Low stakes; explicitly flagged so it isn't silently decided either way.
5. **Finding #9 (ctap-smvod orchestrator shape)** — before starting CSM-2, confirm with whoever implements it that `RunPipeline`'s class diagram is illustrative (steps delegate to the named
   `merge_*.py`/`analyze_*.py` scripts) and not the literal intended class — if literal, revise CSM-2's diagram in `pipeline-migration/ctap-smvod-investigation-migration/stories.md` to show explicit
   delegation before any code is written.
6. **Finding #10 (Athena batch/cache design)** — same gap already flagged in the prior 2026-10-01 conversation (batched/concurrent query submission, SQL-fingerprint result cache, polling backoff).
   Belongs as a new task on `athena-lib-integration` (e.g. an `ALI-5`) once a human decides to scope it — not invented here, since it is a real design task, not a doc fix.
