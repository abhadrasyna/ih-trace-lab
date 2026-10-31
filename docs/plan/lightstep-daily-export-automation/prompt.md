# Lightstep daily export automation — prompt

> Replace the hand-exported daily Lightstep CSVs in `investigations/ctap-smvod/data/lightstep/<TENANT>/` with one script that pulls them through the Lightstep public API.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Every day, someone opens Lightstep notebooks and saves eight CSVs by hand into `data/lightstep/<TENANT>/`: `<date>_ctap.csv`, `<date>_smvod.csv`, `<date>_smvod-ts.csv`, `<date>_mdrmfe.csv`,
`<date>_mdrm-cdm-widevine.csv`, `<date>_mdrm-cdm-fairplay.csv`, `<date>_mdrm-cdm-playready.csv` and `<date>_mdrm-lrm.csv`. It is slow and error-prone, and the UI row limit forces hourly `_NN_` part
files. The Lightstep MCP cannot replace it: every response has to pass through the agent, truncates at 50 series, and a full day is on the order of 100+ calls.

Feasibility was confirmed on 2026-10-31: `POST /public/v0.2/Synamedia-EU/projects/<project>/telemetry/query_timeseries` with an org API token returned HTTP 200 and the same 25 series as the MCP for a
10-minute slice of the ctap playsessions query. A script can therefore slice a UTC day into windows that stay under the 50-series cap, merge the slices, and write the CSVs in the exact format the
pipeline already reads (UTF-8 BOM, every field quoted, columns as exported by the UI).

## Scope guard

In bounds: a new export script and shared helpers under `scripts/`/`scripts/lib/` (or the ctap-smvod equivalents), parameterised query templates in `queries/lightstep/`, docs
(`investigations/ctap-smvod/docs/usage.md`, `lightstep-drm-exports.md`), and `SCRIPTS.md`. Out of bounds: the pipeline steps that consume the CSVs (`merge_ctap_smvod_csv.py` and later), Athena, and
any change to `check_lightstep_inputs.py` behaviour — the new files must pass it unchanged. Tooling only; no runtime change to the existing pipeline. The API token is never committed: it is read from
`LIGHTSTEP_API_KEY_EU` / `LIGHTSTEP_API_KEY_US` in the environment or a gitignored `.env`.

## Session-start load hints

- `docs/guides/tenant-resolution.md` — run `scripts/resolve_tenant.py --system <lightstep_go|lightstep_mdrm> --tenant <X>` for the project and shared-project `busUnitId` filter; never hardcode ids.
- `docs/guides/query-catalog.md` and `queries/lightstep/index.md` — query templates belong in the catalog, not baked into the script.
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — the five DRM exports, their projects (EU vs US) and attribute names.
- `investigations/ctap-smvod/scripts/lib/lightstep_inputs.py` — the validator (columns, part numbering, `smvod-ts` UTC coverage) the generated files must satisfy.
- `investigations/ctap-smvod/scripts/combine_lightstep_parts.py` — existing part-file convention (`_NN_` parts, `.combined-from.json` sidecar).

## Task overview

- **LX-1** — feasibility spike: reproduce one real manual export per kind through the API and diff against it.
- **LX-2** — query templates for the eight exports in `queries/lightstep/` plus a per-kind registry.
- **LX-3** — Lightstep API client with slicing and truncation-driven auto-split.
- **LX-4** — UI-format CSV writer and part-file naming.
- **LX-5** — `export_lightstep_day.py` CLI that pulls all eight kinds for a tenant and date and runs the input check.
- **LX-6** — docs, `SCRIPTS.md` entry, and a parity run against a day that was exported by hand.

## Definition of done

`python3 export_lightstep_day.py --tenant ZA --date 2026-10-29` writes all eight files into `data/lightstep/ZA/`, they pass `check_lightstep_inputs.py`, row counts match the hand-exported day within
the documented tolerance, and the token never appears in the repo. See `tasks.md` "Story done when".

## Perspectives not covered

- Rate limits and quotas of the Lightstep public API for a full day of slices are unknown until LX-1 measures them.
- Scheduling (cron/CI) of the daily pull is out of scope; this story delivers the on-demand command only.
- Token rotation and secret storage beyond a gitignored `.env` are not addressed.
- Nigeria has no registered mDRM tenant id, so its DRM exports cannot be automated yet.
