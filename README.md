# ih-trace-lab

This project's mission is to take the profile of investigative/analysis work already done in `/Users/abhadra/github_copilot` (Synamedia IH/Matisse/Lightstep/Athena debugging: tenant resolution,
session-report pipelines, HAR/trace correlation, ad hoc scratch analysis scripts) and re-implement the reusable parts here with real engineering discipline — tests, typed Python, a documented pre-task
protocol (`AGENTS.md`), and a `scratch/` → `scripts/dev/`/`src/` promotion workflow — instead of the copy-pasted-across-repos style that accumulated there over time. `github_copilot` is a **read-only
reference** for prior art and confirmed domain facts; it is never edited from this project, and it is expected to be replaced by `ih-trace-lab` over time, one story at a time (see `docs/plan/`).

## Status

Early / active. First story (`docs/plan/tenant-registry/`) is not yet implemented; `docs/plan/scratch-script-registry/`, `docs/plan/project-taxonomy/`, and `docs/plan/functional-code-taxonomy/` are
complete; `docs/plan/query-catalog/` is still planned. Reusable project tooling now includes both registry generators under `scripts/dev/`, and production `src/lib/` code has started with shared
Protocol/config layers for `athena`, `report_render`, `har`, and `paths`.

## Setup

Runtime dependencies: `pip install -r requirements.txt` (currently `PyYAML` for config-driven path resolution). Dev tooling: `pip install -r requirements-dev.txt`, then `pre-commit install`.
