# MTN monthly error code analysis retention

`investigations/mtn-monthly-error-code-analysis/` is a rolling recurring campaign, not a one-off case file. Each month appends a fresh Athena pull into `data/athena/<OPCO>/YYYY-MM/`, regenerates the
per-month artifacts under `output/<OPCO>/`, and adds a dated findings doc under `docs/`.

There is no planned close-out date. Retain the structure, scripts, and historical outputs so any month can be re-run with the same pipeline and compared against prior months.

- `data/` is gitignored (repo-root `.gitignore`), so raw Athena pulls stay local and are re-creatable from the query catalog; keep at least the last 3 months locally for re-runs.
- `output/` holds the monthly reports and is retained indefinitely.
- `docs/` dated findings are retained indefinitely.
