# Auth lib migration — prompt

> Consolidate AWS SSO auth helpers duplicated across `github_copilot` into `src/lib/auth/`, defining its `Protocol` here (deferred by `functional-code-taxonomy` FCT-2, which scoped only
> `athena`/`report_render`/`har`) using `athena_runner.sso_auth`'s already-landed shape as prior art.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

**Hard gate:** confirm `docs/plan/functional-code-taxonomy/` FCT-1 is checked done, and `docs/plan/src-lib-migration/athena-lib-integration/` is fully done (this story's `Protocol` uses
`athena_runner.sso_auth`'s public interface as prior art — read it, do not guess at it).

## Why this story exists

`functional-code-taxonomy` named `auth` as one of the six `src/lib/*` modules but deliberately left its `Protocol` unbuilt ("the remaining modules get the same treatment as a follow-up once a real
consumer needs them"). This epic is that consumer. Unlike `report_render`/`har`, this story must *design* the `Protocol` first, not just implement against one — using `athena-mcp-server`'s
`athena_runner.sso_auth`/`sso_profiles` (already a real, tested AWS SSO auto-refresh implementation, landed via `athena-lib-integration`) as the concrete shape to generalize from, rather than
inventing an auth interface from nothing.

## Scope guard

**In scope:** `src/lib/auth/protocols.py` (new `Protocol`, generalized from `athena_runner.sso_auth`'s public surface) + `src/lib/auth/` concrete implementer wrapping AWS SSO profile refresh for
non-Athena consumers; tests; doc/`CONTEXT.md` pointers.

**Out of scope:** re-implementing `athena_runner.sso_auth` itself (this story's concrete class delegates to it where the shape matches, per the same DIP posture as `athena-lib-integration`); any
change under `/Users/abhadra/github_copilot` or inside the `athena-mcp-server` submodule.

## Session-start load hints

- `docs/plan/src-lib-migration/README.md` — epic architecture diagram and constraints.
- `docs/plan/src-lib-migration/athena-lib-integration/stories.md` — the adapter pattern this story's concrete class should mirror.
- `/Users/abhadra/myWork/myOffice/athena-mcp-server/src/athena_runner/sso_auth.py` and `sso_profiles.py` (read-only reference for shape, via the submodule once ALI-1 lands) — the concrete prior art
  this `Protocol` generalizes.
- `docs/plan/functional-code-taxonomy/stories.md` FCT-2 — match its `Protocol` authoring pattern (`@runtime_checkable`, method signatures only) exactly for consistency.
- `PYTHON_DESIGN.md` — DIP trigger section.

## Task overview

- **AUM-1** — `src/lib/auth/protocols.py`: new `AuthProtocol`, generalized from `athena_runner.sso_auth`'s shape, with conformance tests.
- **AUM-2** — `src/lib/auth/sso.py`: concrete implementer delegating to `athena_runner.sso_auth` where applicable.
- **AUM-3** — Tests + `Protocol` conformance pair.
- **AUM-4** — Doc/`CONTEXT.md` pointers.

## Definition of done

- `src/lib/auth/protocols.py` defines a `Protocol`-only interface (no bodies beyond `...`), `@runtime_checkable`, matching FCT-2's authoring style.
- `src/lib/auth/sso.py` implements it, verified via `isinstance`, with no duplicated SSO refresh logic (delegates to `athena_runner.sso_auth`).
- Tests pass with no live AWS calls.
- `CONTEXT.md` gains one new line.

## Perspectives not covered

- This story does not design an auth `Protocol` broad enough for non-AWS auth mechanisms (e.g. OAuth, API keys) — scoped narrowly to AWS SSO profile refresh, the only mechanism with proven prior art
  in this codebase today. A broader `Protocol` is a future story's problem, triggered by a real second auth mechanism appearing.
