# Athena lib integration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: ALI-3, ALI-4, ALI-5, ALI-6, ALI-7.**

- [x] **ALI-1** — Add `athena-mcp-server` as a pinned git submodule + init/update docs | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 2f7bad3
- [x] **ALI-2** — `src/lib/athena/adapter.py` + `exceptions.py`: DIP-compliant `Protocol`-conforming adapter delegating to `athena_runner`, with mirrored exception hierarchy and throttling
  retry/backoff | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: c6bebc3
- [ ] **ALI-3** — Tests: mocked `athena_runner`, `Protocol` conformance pair | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **ALI-4** — Audit: confirm whether `athena_runner` already supports batch/concurrent submission or caching | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review
  | SHA: <—>
- [ ] **ALI-5** — `src/lib/athena/batch.py` + `cache.py`: concurrent batch submission + TTL result cache, FCID-propagating | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human
  confirms tests green | SHA: <—>
- [ ] **ALI-6** — `src/lib/athena/progressive.py`: progressive scope-widening query runner | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **ALI-7** — `CONTEXT.md` + setup docs: submodule + batch/cache/progressive pointer | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **ALI-1** — `.gitmodules` has an `athena-mcp-server` entry pinned to a specific commit; `git submodule update --init` reproduces the checkout from a clean clone; a short doc note states this
  requirement.
- **ALI-2** — `src/lib/athena/adapter.py` exists, contains no ported `query_executor`/`aws_clients` logic (delegation only), and its constructor receives its `athena_runner` collaborator rather than
  constructing it; `src/lib/athena/exceptions.py` defines the module's own exception hierarchy, never leaking `athena_runner.exceptions.*` across the `Protocol` boundary; throttling errors are retried
  with backoff, other errors propagate immediately.
- **ALI-3** — `pytest` passes for the adapter using mocked `athena_runner` calls (no live AWS/network); a `Protocol`-conformance test confirms the adapter satisfies FCT-2's `Protocol` via
  `isinstance`.
- **ALI-4** — A recorded finding states whether `athena_runner` already has batch/concurrent-submission or caching support to delegate to, or confirms ALI-5 is net-new design (added 2026-10-01 per
  `pre-implementation-design-review` finding #6).
- **ALI-5** — `src/lib/athena/batch.py`'s `BatchQueryRunner` submits independent queries concurrently (bounded pool sized from `RunConfig.max_concurrency`), carries the caller's FCID into worker
  threads via `contextvars.copy_context()`, never constructs an `AthenaClient` from inside a worker thread, and `cache.py`'s `InMemoryTtlCache` serves repeated identical SQL+params from cache within
  its TTL; `pytest` passes including the FCID-propagation, concurrency-bound, and TTL-expiry tests.
- **ALI-6** — `src/lib/athena/progressive.py`'s `ProgressiveQueryRunner` runs a query against a narrow scope first, widens only when a `SufficiencyCheck` says the result isn't enough, stops when
  `ScopeSequence` is exhausted, and returns rows combined across every scope actually run (not just the last); `pytest` passes including the stop-at-first-sufficient and combine-across-scopes tests.
- **ALI-7** — `CONTEXT.md`'s "What Exists" gains lines for the adapter, the batch/cache layer, and the progressive-scope layer; this project's setup/README documents `git submodule update --init
  --recursive` as a required setup step.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
