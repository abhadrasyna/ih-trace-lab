# MTN monthly error code analysis script usage

All commands run from the repo root with the project venv active. Months are `YYYY-MM`. Raw Athena pulls go to `investigations/mtn-monthly-error-code-analysis/data/athena/<OPCO>/YYYY-MM/`, and reports
go to `investigations/mtn-monthly-error-code-analysis/output/<OPCO>/`. OpCo codes follow the aws_access_cli pipeline: `ZA` (South Africa; `SA` in `config/tenants.yaml`), `NG`, `ZM`, `GH`. Data source
is Athena only.

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

## 3. Error-code classification evidence (MEC-27 input, GH flattened eventdata)

Both scripts read `<date>_<code>.csv` files of flattened `PLAYER_ERROR` events (for example `data/reference/GH/`), dedupe on `messageid`, count distinct sessions, and print counts only (no household,
device or session ids). Shared code is in `scripts/mec_lib/`. A column missing from a day's file prints as "(column absent)", meaning never populated that day, not zero.

### `scripts/profile_error_code.py`

- **Purpose:** per-day evidence profile of one error code: events, sessions, households, devices, sessions per household, and the value distribution of the error text, Shaka fields, MDRM wrapper,
  `pipeline_status`, timing signals (`position` bucketed 0 / >0, `player_phase`, `player_readystate`), `is_wv`, `app_version`, `clibversion` and user-agent family.
- **Args:** `--code 3016`, `--input-dir <folder>`, `--dates YYYY-MM-DD ...` (optional).
- **Example:** `python investigations/mtn-monthly-error-code-analysis/scripts/profile_error_code.py --code 3016 --input-dir investigations/mtn-monthly-error-code-analysis/data/reference/GH`

### `scripts/summarize_error_devices.py`

- **Purpose:** device breakdown of one error code (model, Android version, build id from the user agent, as in `webview_device_summary_report`), split by `is_wv`; events whose user agent has no
  Android build segment appear as `(unparsed)` with their OS family (iOS, macOS, ...).
- **Args:** `--code`, `--input-dir`, `--dates` (optional), `--with-build`, `--top N`.
- **Limit:** iPhone and Mac user agents carry no device model, so non-Android codes only break down by OS family.
