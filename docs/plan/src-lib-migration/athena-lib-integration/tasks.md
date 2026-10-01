# Athena lib integration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: ALI-1, ALI-2, ALI-3, ALI-4, ALI-5, ALI-6.**

- [ ] **ALI-1** — Add `athena-mcp-server` as a pinned git submodule + init/update docs | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **ALI-2** — `src/lib/athena/adapter.py`: DIP-compliant `Protocol`-conforming adapter delegating to `athena_runner` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human
  confirms tests green | SHA: <—>
- [ ] **ALI-3** — Tests: mocked `athena_runner`, `Protocol` conformance pair | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **ALI-4** — Audit: confirm whether `athena_runner` already supports batch/concurrent submission or caching | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review
  | SHA: <—>
- [ ] **ALI-5** — `src/lib/athena/batch.py` + `cache.py`: concurrent batch submission + TTL result cache | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green |
  SHA: <—>
- [ ] **ALI-6** — `CONTEXT.md` + setup docs: submodule + batch/cache pointer | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **ALI-1** — `.gitmodules` has an `athena-mcp-server` entry pinned to a specific commit; `git submodule update --init` reproduces the checkout from a clean clone; a short doc note states this
  requirement.
- **ALI-2** — `src/lib/athena/adapter.py` exists, contains no ported `query_executor`/`aws_clients` logic (delegation only), and its constructor receives its `athena_runner` collaborator rather than
  constructing it.
- **ALI-3** — `pytest` passes for the adapter using mocked `athena_runner` calls (no live AWS/network); a `Protocol`-conformance test confirms the adapter satisfies FCT-2's `Protocol` via
  `isinstance`.
- **ALI-4** — A recorded finding states whether `athena_runner` already has batch/concurrent-submission or caching support to delegate to, or confirms ALI-5 is net-new design (added 2026-10-01 per
  `pre-implementation-design-review` finding #6).
- **ALI-5** — `src/lib/athena/batch.py`'s `BatchQueryRunner` submits independent queries concurrently (bounded pool) and `cache.py`'s `InMemoryTtlCache` serves repeated identical SQL+params from cache
  within its TTL, both via constructor-injected collaborators (DIP); `pytest` passes including the cache-hit-skips-Athena-call and TTL-expiry tests.
- **ALI-6** — `CONTEXT.md`'s "What Exists" gains lines for both the adapter and the batch/cache layer; this project's setup/README documents `git submodule update --init --recursive` as a required
  setup step.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
