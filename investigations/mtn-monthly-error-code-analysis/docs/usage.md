# MTN monthly error code analysis script usage

All commands run from the repo root with the project venv active. Months are `YYYY-MM`. Raw Athena pulls go to `investigations/mtn-monthly-error-code-analysis/data/athena/<OPCO>/YYYY-MM/`, and reports
go to `investigations/mtn-monthly-error-code-analysis/output/<OPCO>/`. OpCo codes come from `config/tenants.yaml` (`SA`, `NG`, `ZM`, `GH`). Data source is Athena only.

## 0. Prerequisites

1. Refresh AWS SSO before any Athena run (`refresh_athena_sso` MCP tool or the SSO preflight in `src/lib/athena/`).
2. Resolve OpCo identifiers with `python scripts/resolve_tenant.py ...` per `docs/guides/tenant-resolution.md`; never guess tenant ids.
3. Reusable building blocks: `src/lib/athena/adapter.py` (query execution), `src/lib/csv_io/monthly_store.py` (monthly CSV upsert), `config/tenants.yaml` (OpCo registry).

## 1. Monthly run order

No scripts exist yet; the entries below are filled in as each script is added.

| Step | Script | Purpose |
|---|---|---|
| 1 | (TBD) | Pull per-OpCo error-code counts for a month from Athena |
| 2 | (TBD) | Merge/aggregate across OpCos into the monthly report |
| 3 | (TBD) | Month-over-month comparison |

## 2. Per-script entry template

Copy this block for each new script, and also register it in `SCRIPTS.md`.

### `scripts/<name>.py`

- **Purpose:** one sentence.
- **Args:** `--month YYYY-MM`, `--opco <CODE>` (optional; default all), others.
- **Inputs:** files or Athena catalog query ids read.
- **Outputs:** paths written under `data/` or `output/`.
- **Example:**

```bash
python investigations/mtn-monthly-error-code-analysis/scripts/<name>.py --month 2026-09 --opco ZM
```
