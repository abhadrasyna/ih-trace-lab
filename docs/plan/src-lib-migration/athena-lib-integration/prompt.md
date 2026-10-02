# Athena lib integration — prompt

> Wire the already-independent `athena-mcp-server` repo in as a git submodule and adapt `src/lib/athena/` to it — do not reimplement `query_executor`/`aws_clients` a fifth time.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/archive/functional-code-taxonomy/` FCT-1 and FCT-2 are checked done in that story's `tasks.md` before starting ALI-2 or later — FCT-2 is where `src/lib/athena/`'s
`Protocol` shape is defined; this story implements against it, not around it. ALI-1 (the submodule add) has no such dependency and may proceed independently if useful, but do not skip ahead past it.

## Why this story exists

Auditing `/Users/abhadra/myWork/myOffice/athena-mcp-server` while scoping this epic found the Athena duplication problem `functional-code-taxonomy` documented (four independent copies of the same
start/poll/download pattern across `github_copilot`) already solved *outside* `ih-trace-lab`: `athena-mcp-server` is a fully independent, tested (101 tests), pip-installable repo whose
`src/athena_runner/*` (`config`, `aws_clients`, `query_executor`, `result_downloader`, `sso_auth`, `sso_profiles`, `tenants`, `logging_setup`, `date_utils`, `exceptions`) is exactly that shared
execution stack — itself ported from `github_copilot/oasis-athena-mcp` (originally `aws-access-cli/scripts/athena_runner/`). It is not yet wired into `ih-trace-lab`. Re-porting that logic into
`src/lib/athena/` would recreate the exact problem this epic exists to stop — a fifth copy instead of zero.

So this story is integration, not migration: add the repo as a git submodule, then write a thin adapter in `src/lib/athena/` that satisfies `functional-code-taxonomy` FCT-2's `Protocol` by delegating
to `athena_runner`'s existing classes — constructor-injected per `PYTHON_DESIGN.md`'s DIP trigger ("a class constructs its own collaborator directly instead of receiving it"), never re-implemented.
**2026-10-01 addition (`pre-implementation-design-review` finding #6, scoped via follow-up questions):** real investigations submit small batches of independent queries (2-5, e.g. per-tenant/per-day
fan-out) and sometimes re-run identical SQL+params — ALI-4/ALI-5 add bounded-concurrency batch submission and a TTL result cache on top of the single-query adapter, rather than leaving every consumer
to hand-roll its own `ThreadPoolExecutor`/caching. **2026-10-01 extended design review (same day, follow-up pass):** also closed a real cross-cutting gap (`flow-correlation-id-logging`'s own FCID
design does not survive a `ThreadPoolExecutor` boundary without an explicit fix — ALI-5 now wires that fix in), added a mirrored `src/lib/athena/exceptions.py` hierarchy and throttling retry/backoff
to ALI-2 (confirmed missing upstream in `athena_runner.query_executor`), confirmed `athena_runner.config.RunConfig.max_concurrency` is an already-reserved-but-unconsumed config field ALI-5 should
honor rather than duplicate, flagged `AwsClientFactory`'s shared-`boto3.Session` client construction as unsafe to call concurrently from worker threads (ALI-5 pre-builds clients up front instead), and
added ALI-6 (`progressive.py`) for the requester's own scoping request: run a query against a narrow scope first, widen only if insufficient, and combine rows across every scope actually run.

## Locked-in decisions (requester-approved 2026-10-02)

- **Submodule path:** `vendor/athena-mcp-server`.
- **Submodule pin:** pin to the commit that is `athena-mcp-server`'s `HEAD` at the time ALI-1 is executed (confirmed `9463d00` as of 2026-10-02) — never track `main`.

## Scope guard

**In scope:** `.gitmodules` entry + pinned submodule checkout of `athena-mcp-server`; `src/lib/athena/adapter.py` + `exceptions.py` (thin delegation layer, with a mirrored exception hierarchy and
throttling retry/backoff); `src/lib/athena/batch.py` + `cache.py` (concurrent batch submission + TTL result cache, FCID-propagating, built on top of the adapter, not inside it);
`src/lib/athena/progressive.py` (progressive scope-widening query runner); tests mocking `athena_runner`'s public surface (no live AWS); doc/`CONTEXT.md` pointers.

**Out of scope:** any change inside the `athena-mcp-server` submodule itself once added (it is a separate repo with its own commit history and its own `AGENTS.md`/test suite — treat it as externally
owned, same posture as `/Users/abhadra/github_copilot` but for a different reason: here it's because it's a *sibling deliverable*, not because it's a read-only audit target); any change under
`/Users/abhadra/github_copilot`; `functional-code-taxonomy`'s own FCT-1/FCT-3 citations (this story leaves the coordination note in the epic `README.md` instead of editing that story's files directly,
since that story is owned separately and not yet started); a distributed/persistent cache backend (`InMemoryTtlCache` only — a Redis/file-backed `QueryResultCache` implementer is a future consumer's
problem if ever needed, kept open via the `Protocol` seam); fixing `athena_runner.query_executor`'s own lack of throttling retry upstream (that belongs to that repo's own backlog — this story's
adapter adds resilience at its own boundary instead).

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — the epic architecture diagram and cross-cutting constraints this story must honour.
- `docs/archive/functional-code-taxonomy/prompt.md` + `stories.md` (FCT-2 spec) — the exact `Protocol` shape `src/lib/athena/adapter.py` must satisfy.
- `docs/archive/flow-correlation-id-logging/stories.md` — the FCID convention and its own stated `contextvars`/`ThreadPoolExecutor` caveat, which ALI-5 must satisfy.
- `/Users/abhadra/myWork/myOffice/athena-mcp-server/CONTEXT.md` and `README.md` — what `athena_runner` already exposes, and its one known open item (the `aws-access-cli` sibling-checkout
  namespace-package merge in `tool_config.py::_load_mtn_registry`) — this story's adapter must not silently mask that fragility if it surfaces during integration.
- `PYTHON_DESIGN.md` — cite the specific DIP trigger this story applies before writing `adapter.py`, the Strategy/concurrency guidance before writing `batch.py`/`cache.py`, and the Template
  Method/Iterator guidance before writing `progressive.py`.

## Task overview

- **ALI-1** — Add `athena-mcp-server` as a pinned git submodule; document init/update steps.
- **ALI-2** — `src/lib/athena/adapter.py` + `exceptions.py`: DIP-compliant adapter implementing FCT-2's `Protocol` by delegating to `athena_runner.query_executor`/`aws_clients`, with a mirrored
  exception hierarchy and throttling retry/backoff.
- **ALI-3** — Tests (mocked `athena_runner`, no live AWS) + `Protocol` conformance check.
- **ALI-4** — Audit whether `athena_runner` already supports batch/concurrent submission or caching, before designing ALI-5.
- **ALI-5** — `src/lib/athena/batch.py` + `cache.py`: bounded-concurrency, FCID-propagating batch submission + TTL result cache, constructor-injected over the ALI-2 adapter.
- **ALI-6** — `src/lib/athena/progressive.py`: progressive scope-widening query runner.
- **ALI-7** — Doc/`CONTEXT.md` pointers; note submodule init requirement in project `README.md` setup steps.

## Definition of done

- `athena-mcp-server` is a real git submodule at a pinned commit; `git submodule update --init` reproduces it; the epic `README.md` "Stories" status column is updated.
- `src/lib/athena/adapter.py` contains no port of `query_executor`/`aws_clients` logic — only delegation; it satisfies FCT-2's `Protocol` via `isinstance` in a test; its own `exceptions.py` hierarchy
  is what every method raises, never a raw `athena_runner.exceptions.*` type.
- `src/lib/athena/batch.py`'s `BatchQueryRunner` and `cache.py`'s `InMemoryTtlCache` exist, both DIP-compliant (constructor-injected collaborators, no silent default construction); FCID survives into
  every worker thread.
- `src/lib/athena/progressive.py`'s `ProgressiveQueryRunner` exists, DIP-compliant, and combines rows across every scope actually run.
- Tests pass with zero live AWS calls.
- `CONTEXT.md` and this project's setup docs each note the new submodule dependency and the batch/cache/progressive layers.

## Perspectives not covered

- This story does not resolve `athena-mcp-server`'s own open `tool_config.py` sibling-checkout fragility — that belongs to that repo's own backlog. It only ensures this story's adapter does not depend
  on the fragile part (`tool_config.py`'s MTN registry), only on the generic `athena_runner` execution stack.
- This story does not add a persistent/shared cache backend, a distributed lock for cross-process batch coordination, or cross-process FCID propagation (subprocess/cron boundaries) — all three stay
  explicitly out of scope per `flow-correlation-id-logging`'s own stated scope guard.
