# shaka-6001

Investigation of Shaka error code 6001 across the ZA, GH and ZM tenants.

## Questions

1. Which device models are impacted by 6001?
2. How many of the impacted devices have `drmenabled` set in the debug table?

## Data sources

Local data first, from `investigations/ctap-smvod/`:

- `output/error_code/6001/*_error_6001_by_opco.xlsx` (per-opco 6001 sessions)
- `output/<TENANT>/daily/*_shaka-error-{session,hhid}.csv`
- flat error eventdata (`*_error_eventdata*.csv`, see `ctap-smvod/docs/usage.md`)

Anything missing locally is fetched by a script in `scripts/` from Athena (debug events) or Lightstep, never by ad hoc queries.

## Layout

- `data/` gitignored local inputs
- `output/` gitignored generated reports
- `scripts/` single-purpose scripts, registered in the root `SCRIPTS.md`
- `tests/` offline tests
- `docs/` findings and notes
