# ih-trace-lab

This project's mission is to take the profile of investigative/analysis work already done in `/Users/abhadra/github_copilot` (Synamedia IH/Matisse/Lightstep/Athena debugging: tenant resolution,
session-report pipelines, HAR/trace correlation, ad hoc scratch analysis scripts) and re-implement the reusable parts here with real engineering discipline — tests, typed Python, a documented pre-task
protocol (`AGENTS.md`), and a `scratch/` → `scripts/dev/`/`src/` promotion workflow — instead of the copy-pasted-across-repos style that accumulated there over time. `github_copilot` is a **read-only
reference** for prior art and confirmed domain facts; it is never edited from this project, and it is expected to be replaced by `ih-trace-lab` over time, one story at a time (see `docs/plan/`).

## Status

Early / active. First story (`docs/archive/tenant-registry/`) is not yet implemented; `docs/archive/scratch-script-registry/`, `docs/archive/project-taxonomy/`, and
`docs/archive/functional-code-taxonomy/` are complete; `docs/archive/query-catalog/` is still planned. Reusable project tooling now includes both registry generators under `scripts/dev/`, and
production `src/lib/` code has started with shared Protocol/config layers for `athena`, `report_render`, `har`, and `paths`.

2026-10-04 coordination note: root `scripts/dev/` entry points are not retrofitted to `src/lib/logging/bootstrap.py`'s `init_logging()` by `docs/plan/logging-framework/`; that story only wires the
`aws_access_cli` pipeline. The existing `setup_logging()` callers (`scripts/dev/harvest_athena_query_catalog.py`, `scripts/dev/harvest_lightstep_query_catalog.py`) should migrate next time they are
touched, and the remaining `scripts/dev/*.py` entry points need their own follow-up ownership before code changes.

## Setup

Runtime dependencies: `pip install -r requirements.txt` (currently `PyYAML` for config-driven path resolution). Dev tooling: `pip install -r requirements-dev.txt`, then `pre-commit install`.

This repo has a git submodule (`vendor/athena-mcp-server`) — after cloning, run `git submodule update --init --recursive` (or clone with `git clone --recurse-submodules`). See
`docs/guides/submodules.md` for what it provides and how to update its pin.
