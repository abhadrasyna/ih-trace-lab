# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `docs/plan/tenant-registry/` — story: canonical MTN tenant-identifier config (Go ID, Matisse Project/Client Tenant ID, Athena Tenant ID, Lightstep project/region, shared-project disambiguation) +
  a resolver this assistant must consult before any Lightstep/Matisse/Athena MCP call. Not yet implemented — see its `tasks.md` for the first unchecked task (TR-1).

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- (anything a session must not violate — e.g. "no network calls in tests", a data format that's frozen, a dependency that can't be upgraded yet)

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
