# Conviva Metrics Recreation — epic index

> Recreate Conviva-style playback statistics (attempts, concurrent plays, VPF, VSF, EBVS, and related) from locally held session data, Lightstep and Athena, so Conviva numbers can be cross-checked.

## Why this epic exists

Conviva reports headline playback statistics that investigations rely on but cannot inspect or reproduce. Recomputing them from our own trace/session data lets us verify Conviva numbers, explain
discrepancies, and extend the metrics to cases Conviva does not cover. It is an epic rather than one story because each metric family has its own definition, event mapping and validation.

## Scope decisions

- Confirmed with the user, 2026-10-26: this phase is story/epic documentation only — no code, no tests.
- Metric definitions come from Conviva's own documentation; the user will supply or point to it. Do not invent definitions.
- Data sourcing order: use data already held locally first; fetch new data from Lightstep or Athena only when local data is insufficient.
- Implementation starts as `scratch/` scripts to test feasibility (per `scratch/SCRATCH.md`), and graduates to `src/`/`scripts/` only after a separate go-ahead.
- Initial metric set: attempts, concurrent plays, VPF (video playback failures), VSF (video start failures), EBVS (exits before video start). More may be added after the definitions story.

## Stories

| Story | Purpose | Status | Depends on | Closing SHA |
|---|---|---|---|---|
| `metric-definitions-data-inventory/` | Capture Conviva definitions and inventory local/Lightstep/Athena data per metric | ⬜ Not started | — | — |
| `attempts/` | Recreate attempts (POC done on ZA, 2026-10-24; formal recreation open, runs after `concurrent-plays/`) | 🔄 In progress | `concurrent-plays` (CMR-CP-2, CMR-CP-6) | — |
| `attempts-concurrent-plays/` | Placeholder; attempts moved to `attempts/` and concurrent plays to `concurrent-plays/` (left untouched) | ⬜ Not started | `metric-definitions-data-inventory` | — |
| `concurrent-plays/` | Recreate concurrent plays (POC, chart and report accepted on ZA, 2026-10-24: peak 16; CMR-CP-1 done; raw export, gaps and formal recreation open) | 🔄 In progress | — | — |
| `cir-related-exits/` | Recreate CIR Related Exits (POC accepted, ZA 2026-10-24: 19.40%; formal recreation open) | 🔄 In progress | `concurrent-plays` (CMR-CP-2, CMR-CP-6) | — |
| `vpf-vsf/` | Recreate VPF and VSF, including error classification | ⬜ Not started | `metric-definitions-data-inventory` | — |
| `ebvs/` | Recreate EBVS (exits before video start) | ⬜ Not started | `attempts` | — |
| `scratch-validation/` | Compare recomputed numbers against Conviva and record gaps | ⬜ Not started | `vpf-vsf`, `ebvs` | — |

Status: ⬜ Not started · 🔄 In progress · ✅ Done. This column is the epic's progress view — per-task checkboxes live only in each sub-story's `tasks.md`.

## Cross-cutting constraints

- Every metric must cite the Conviva definition it implements, with the doc reference, in its script header and in the story output.
- Before any Lightstep/Matisse/Athena call, run `python scripts/resolve_tenant.py ...` and follow `docs/guides/tenant-resolution.md`; never guess tenant ids.
- Scratch scripts follow `scratch/SCRATCH.md` (duplicate-check, registry stub) and the query catalog rules in `docs/guides/query-catalog.md`.
- Tests are offline: no network, fixtures from local data only.

## Supersession / coordination

Overlaps in subject matter with `docs/plan/session-trace-analysis/` (session lifecycle, presence funnel, error model). Reuse its session and error classification rather than re-deriving them; check
its status before starting `vpf-vsf`.

## Epic done when

- **metric-definitions-data-inventory** — each metric has a sourced definition and a mapped data source, with gaps listed.
- **attempts-concurrent-plays** — both metrics recomputed from session data with a documented method.
- **vpf-vsf** — both failure metrics recomputed with an explicit error-to-metric classification.
- **ebvs** — EBVS recomputed and distinguished from VSF.
- **scratch-validation** — recomputed values compared with Conviva for at least one real window, with discrepancies explained or logged.
