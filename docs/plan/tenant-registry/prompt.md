# Tenant registry — prompt

> One-line statement of what this story delivers.

A single canonical, extensible tenant-identifier config (Go ID, Matisse Project ID, Matisse Client Tenant ID, Athena Tenant ID, Lightstep project/region, shared-project disambiguation) plus a
resolver that a human, a script, or this assistant must consult before any Lightstep/Matisse/Athena MCP call — so a wrong tenant ID can never silently reach a real query.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else.
Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task.
Read that task's full spec in `stories.md` (same task id) before writing any code.
One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot` grew its tenant-ID handling ad hoc, one investigation at a time, and it broke down: the only tenant registry that exists (`aws-access-cli/scripts/athena_runner/tenants.py`)
covers Athena IDs only, is copy-pasted near-verbatim into a second repo (`mtn-zm-session-device-investigation`) instead of shared, and only knows 2–4 tenants each. Go ID, Matisse Project ID, Matisse
Client Tenant ID, and the `sessionInfo.busUnitId` disambiguation needed for shared Lightstep projects (e.g. Zambia + Ghana both live in `mcs-go-prod-mtn-1-eu`) have **no registry at all** — they exist
only as string literals scattered across markdown docs and JSON fixtures. No YAML/config file anywhere lets a script — or this assistant — look up "which tenant ID do I use for Ghana's Lightstep GO
query" without re-deriving it from memory each time.

Every wrong tenant pick costs a real MCP round-trip (tokens + time) against the wrong data. `ih-trace-lab` is meant to eventually replace `github_copilot` as the working environment; this registry is
its first piece, and it must not repeat `github_copilot`'s mistake of assuming "1 opco = 1 project" — Zambia/Ghana sharing a Lightstep project is a first-class case from day one, not a later patch.

## Scope guard

**In scope:** the 4 currently-confirmed MTN opcos (South Africa, Nigeria, Zambia, Ghana) across 3 systems (Lightstep GO/IH, Matisse client-identity, Athena). Config + a thin Python loader/resolver +
a CLI wrapper this assistant shells out to before invoking a Lightstep/Matisse/Athena MCP tool + a short protocol doc.

**Out of scope:** TIM Play/mileto, Astro GO, MTN Zambia's HAR-derived alternate IDs (unresolved 2nd source, see prior session note), mDRM backend tenant IDs, any live automated Lightstep/Athena client
in `src/` (only the existing MCP tools are used to *query*; this story only resolves *which* tenant/project/filter to use). No changes to `/Users/abhadra/github_copilot` itself — read-only reference.
This story changes docs + adds new Python code/config under `ih-trace-lab`; it does not change runtime behaviour of any existing system.

## Session-start load hints

- `docs/guides/tenant-resolution.md` (created by TR-5) — the protocol this assistant must follow before any Lightstep/Matisse/Athena MCP call, once it exists.
- External reference (read-only, not part of this repo): `aws-access-cli/scripts/athena_runner/tenants.py` in `/Users/abhadra/github_copilot` — prior art for the `TenantConfig`/registry shape, and
  the exact duplication problem this story fixes.
- `PYTHON_DESIGN.md` — read before TR-3 (the `Protocol`/`QueryTarget` design must follow its SOLID triggers, not branch on system type in one method).

## Task overview

- **TR-1** — Scratch probe: prove tenant resolution + a real Lightstep MCP round-trip works for one dedicated-project opco (SA) and one shared-project opco (Ghana or Zambia), before writing any
  production code.
- **TR-2** — `config/tenants.yaml`: canonical config for all 4 MTN opcos, informed by TR-1's findings.
- **TR-3** — `src/tenant_registry/`: `TenantConfig`, `TenantRegistry`, `QueryTarget` `Protocol` + one implementer per system (Lightstep GO, Matisse, Athena).
- **TR-4** — `scripts/resolve_tenant.py`: CLI wrapper this assistant invokes via `bash` before any Lightstep/Matisse/Athena MCP call.
- **TR-5** — `docs/guides/tenant-resolution.md` + a one-line `AGENTS.md` pointer (in its existing `<!-- INSERT: investigations -->` slot) making the CLI step mandatory.
- **TR-6** — Tests: registry load/lookup (happy + unknown-id error), each `QueryTarget`'s `build_context` (happy + shared-project-without-`busUnitId` rejection), a CLI smoke test.

## Definition of done

- All 4 MTN opcos resolvable by any of their 4 ID types, via both the Python API and the CLI.
- A shared-project (Zambia/Ghana) Lightstep resolution without a valid `busUnitId` fails loudly instead of silently returning a broad/wrong query.
- Adding/removing/updating a tenant requires editing `config/tenants.yaml` only — no change needed in `src/`, `scripts/`, or `AGENTS.md`.
- `AGENTS.md` gained exactly one short pointer line; no tenant data resident there.
- Tests green; `docs/plan/tenant-registry/tasks.md` fully checked off with real commit SHAs.

## Perspectives not covered

- Whether Matisse and Athena MCP calls need the same "reject on missing disambiguation" enforcement Lightstep GO needs — only Lightstep's shared-project case (Zambia/Ghana) is confirmed today; Matisse/
  Athena are assumed 1:1 per opco but this hasn't been stress-tested the way Lightstep GO was.
- What happens when a 5th MTN opco or a non-MTN tenant (TIM Play, Astro) is added — the config/registry shape should support it (no code change), but onboarding one is not exercised by this story.
