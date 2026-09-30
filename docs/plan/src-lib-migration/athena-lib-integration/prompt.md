# Athena lib integration — prompt

> Wire the already-independent `athena-mcp-server` repo in as a git submodule and adapt `src/lib/athena/` to it — do not reimplement `query_executor`/`aws_clients` a fifth time.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/plan/functional-code-taxonomy/` FCT-1 and FCT-2 are checked done in that story's `tasks.md` before starting ALI-2 or later — FCT-2 is where `src/lib/athena/`'s `Protocol`
shape is defined; this story implements against it, not around it. ALI-1 (the submodule add) has no such dependency and may proceed independently if useful, but do not skip ahead past it.

## Why this story exists

Auditing `/Users/abhadra/myWork/myOffice/athena-mcp-server` while scoping this epic found the Athena duplication problem `functional-code-taxonomy` documented (four independent copies of the same
start/poll/download pattern across `github_copilot`) already solved *outside* `ih-trace-lab`: `athena-mcp-server` is a fully independent, tested (101 tests), pip-installable repo whose
`src/athena_runner/*` (`config`, `aws_clients`, `query_executor`, `result_downloader`, `sso_auth`, `sso_profiles`, `tenants`, `logging_setup`, `date_utils`, `exceptions`) is exactly that shared
execution stack — itself ported from `github_copilot/oasis-athena-mcp` (originally `aws-access-cli/scripts/athena_runner/`). It is not yet wired into `ih-trace-lab`. Re-porting that logic into
`src/lib/athena/` would recreate the exact problem this epic exists to stop — a fifth copy instead of zero.

So this story is integration, not migration: add the repo as a git submodule, then write a thin adapter in `src/lib/athena/` that satisfies `functional-code-taxonomy` FCT-2's `Protocol` by delegating
to `athena_runner`'s existing classes — constructor-injected per `PYTHON_DESIGN.md`'s DIP trigger ("a class constructs its own collaborator directly instead of receiving it"), never re-implemented.

## Scope guard

**In scope:** `.gitmodules` entry + pinned submodule checkout of `athena-mcp-server`; `src/lib/athena/adapter.py` (thin delegation layer only); tests mocking `athena_runner`'s public surface (no live
AWS); doc/`CONTEXT.md` pointers.

**Out of scope:** any change inside the `athena-mcp-server` submodule itself once added (it is a separate repo with its own commit history and its own `AGENTS.md`/test suite — treat it as externally
owned, same posture as `/Users/abhadra/github_copilot` but for a different reason: here it's because it's a *sibling deliverable*, not because it's a read-only audit target); any change under
`/Users/abhadra/github_copilot`; `functional-code-taxonomy`'s own FCT-1/FCT-3 citations (this story leaves the coordination note in the epic `README.md` instead of editing that story's files directly,
since that story is owned separately and not yet started).

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — the epic architecture diagram and cross-cutting constraints this story must honour.
- `docs/plan/functional-code-taxonomy/prompt.md` + `stories.md` (FCT-2 spec) — the exact `Protocol` shape `src/lib/athena/adapter.py` must satisfy.
- `/Users/abhadra/myWork/myOffice/athena-mcp-server/CONTEXT.md` and `README.md` — what `athena_runner` already exposes, and its one known open item (the `aws-access-cli` sibling-checkout
  namespace-package merge in `tool_config.py::_load_mtn_registry`) — this story's adapter must not silently mask that fragility if it surfaces during integration.
- `PYTHON_DESIGN.md` — cite the specific DIP trigger this story applies before writing `adapter.py`.

## Task overview

- **ALI-1** — Add `athena-mcp-server` as a pinned git submodule; document init/update steps.
- **ALI-2** — `src/lib/athena/adapter.py`: DIP-compliant adapter implementing FCT-2's `Protocol` by delegating to `athena_runner.query_executor`/`aws_clients`.
- **ALI-3** — Tests (mocked `athena_runner`, no live AWS) + `Protocol` conformance check.
- **ALI-4** — Doc/`CONTEXT.md` pointers; note submodule init requirement in project `README.md` setup steps.

## Definition of done

- `athena-mcp-server` is a real git submodule at a pinned commit; `git submodule update --init` reproduces it; the epic `README.md` "Stories" status column is updated.
- `src/lib/athena/adapter.py` contains no port of `query_executor`/`aws_clients` logic — only delegation; it satisfies FCT-2's `Protocol` via `isinstance` in a test.
- Tests pass with zero live AWS calls.
- `CONTEXT.md` and this project's setup docs each note the new submodule dependency.

## Perspectives not covered

- This story does not resolve `athena-mcp-server`'s own open `tool_config.py` sibling-checkout fragility — that belongs to that repo's own backlog. It only ensures this story's adapter does not depend
  on the fragile part (`tool_config.py`'s MTN registry), only on the generic `athena_runner` execution stack.
