# CTAP/SM-VOD multi-tenant support — prompt

> Make `investigations/ctap-smvod/` run for any tenant in `config/tenants.yaml` (pilot: Zambia), by default for every tenant that has input for the requested date.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The CTAP/SM-VOD pipeline (`scripts/run_pipeline.py`) is single-tenant: inputs live in `data/lightstep/` and `data/athena/`, outputs in `output/`, with nothing namespaced by tenant. Zambia (ZM) must be
supported now and other MTN opcos later. Zambia shares a Lightstep project (`mcs-go-prod-mtn-1-eu`) with Ghana, disambiguated by `sessionInfo.busUnitId`, so a wrong-tenant row is a real risk.

Decisions taken (2026-10-08): "enhance" means multi-tenant support only; `run_pipeline.py` runs every tenant discovered in the input for the requested date by default, and `--tenant <code>` restricts
it to one tenant; existing SA files are `git mv`'d under a tenant folder; in an all-tenants run one tenant's failure does not stop the others (failures are reported at the end, exit non-zero).

## Layout (target)

- Inputs: `data/lightstep/<TENANT>/YYYY-MM-DD_{ctap,smvod,smvod-ts}.csv` and `data/athena/<TENANT>/YYYY-MM-DD_{session,debug_states}.csv`. A tenant is "available" for a date when its Lightstep folder
  holds that date's files.
- Outputs: `output/<TENANT>/YYYY-MM-DD_*.csv` (same file names as today); rollups (e.g. `mtn_escalation_*_rollup.csv`) also per tenant. No cross-tenant merging.
- Tenant identifiers (Athena tenant id, profile, region, Lightstep project, disambiguation attribute) come only from `config/tenants.yaml` via `src/tenant_registry`, resolved once in
  `run_pipeline.py`.

## Scope guard

In bounds: `investigations/ctap-smvod/{scripts,tests,docs,data,output}`, `config/data_paths.yaml`, `src/tenant_registry` (read-only use; extend only if a gap is proven). Out of bounds: other
investigations, the Lightstep export automation (still manual, ~1000-row cap), cross-tenant comparison reports, renaming `mtn_escalation_*`. Changes runtime behaviour (path layout + CLI).

## Design constraints — `docs/refactor/` (so future enhancements stay consistent)

Every task follows the playbook in `docs/refactor/`: `design-principles.md` (SRP/OCP/DIP triggers; tenant context is an injected value, never read ad hoc by each script),
`code-deduplication-and-taxonomy.md` (extend `scripts/lib/runtime.py` path helpers once rather than editing each script; check `SCRIPTS.md`/`src/lib` for prior art first), `planning-protocol.md` (one
task per session, design review before code), `logging-and-correlation-id.md` (log tenant code on every run line), `process-discipline.md`, `python-hygiene-and-automation.md`, and
`code-review-checklist.md` (run before each commit). Adding a future tenant must be a `config/tenants.yaml` edit plus an input folder — no code change.

## Session-start load hints

`config/tenants.yaml`, `docs/guides/tenant-resolution.md`, `config/data_paths.yaml`, `investigations/ctap-smvod/scripts/lib/runtime.py`, `investigations/ctap-smvod/scripts/run_pipeline.py`,
`investigations/ctap-smvod/docs/usage.md`, and the `docs/refactor/` files named above.

## Task overview

- **MT-1** — read-only audit of tenant-specific hardcoding; write findings into this story.
- **MT-2** — path namespacing in `runtime.py` + `data_paths.yaml`.
- **MT-3** — tenant context resolution and discovery; Athena steps consume it.
- **MT-4** — `run_pipeline.py`: all-tenants default, `--tenant`, continue-on-failure.
- **MT-5** — shared-project `busUnitId` guard at merge.
- **MT-6** — migrate existing SA files under a tenant folder.
- **MT-7** — Zambia pilot run for one date and sanity checks.
- **MT-8** — docs (`usage.md`, `CONTEXT.md`) and final review.

## Definition of done

See `tasks.md` "Story done when".

## Perspectives not covered

Automating the Lightstep export or lifting its 1000-row cap; cross-tenant comparison reporting; non-MTN tenants (would need the `mtn_escalation` naming revisited); historical Zambia backfill.
