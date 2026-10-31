# Lightstep daily export automation — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

The eight kinds and their sources (from `investigations/ctap-smvod/docs/lightstep-drm-exports.md` and `docs/usage.md`):

| Kind (file suffix) | Project / region | Tenant system | Notes |
|---|---|---|---|
| `ctap` | GO project, EU | `lightstep_go` | Columns `http.user_agent`, `lightstep.trace_id`, `min/max/avg/sum/value`; `sessionInfo.busUnitId` filter on shared projects. |
| `smvod` | GO project, EU | `lightstep_go` | `householdId`, `deviceId`, `sessionId`, `lightstep.trace_id`; `busUnitId` filter on shared projects. |
| `smvod-ts` | GO project, EU | `lightstep_go` | `sessionId`, `oldest_micros`, `youngest_micros`; must cover the whole UTC day. |
| `mdrmfe` | GO project, EU | `lightstep_go` | `go-mdrmfe` license by session; `span.kind == "server"`; always filtered on `request.tenant` (the tenant's `go_id`), even on a dedicated project. |
| `mdrm-cdm-widevine`, `-fairplay`, `-playready`, `mdrm-lrm` | `mcs-mdrm-production`, US | `lightstep_mdrm` | Always filtered on `tenantId` (the mDRM-internal id); needs the US API token. |

Auth: org API token from `LIGHTSTEP_API_KEY_EU` / `LIGHTSTEP_API_KEY_US` (environment, else the gitignored root `.env`). Both tokens were verified read-only on 2026-10-31 (HTTP 200, expiry in 2027):

| Region | Base URL | Org | Projects confirmed visible |
|---|---|---|---|
| EU | `https://api.eu.lightstep.com/public/v0.2` | `Synamedia-EU` | `mcs-go-prod-iye9omdf-eu` (ZA), `mcs-go-prod-mtn-1-eu` (shared ZM/GH) |
| US | `https://api.lightstep.com/public/v0.2` | `Synamedia` | `mcs-mdrm-production` |

Endpoint verified 2026-10-31: `POST <base>/<org>/projects/<project>/telemetry/query_timeseries`.

## Known queries (2026-10-31)

Three EU queries produce four files; four US queries, one per chart, produce the DRM files. The US queries come from the notebooks `N866YJ6f` (ZA), `HwL92dMR` (ZM) and `5fF1fM0S` (GH), fetched
read-only through the API.

| Kind | Chart / notebook | Query shape |
|---|---|---|
| `ctap` | [VOD-Trace-Join] CTAP CreatePlaySession — User-Agent | `filter http.route == "/ctap/:uxApiVersion/devices/me/playsessions"`; `group_by ["http.user_agent","lightstep.trace_id"], sum` |
| `smvod` + `smvod-ts` | [VOD-Trace-Join] SM-VOD SetupSession — Session Identity | `filter service in (sm-linear, sm-vod) && session.api == "SetupSession" && span.kind == "server"`; 8 labels |
| `mdrmfe` | [ZA] MTN 3016 – mdrmfe license by session | `filter service == "go-mdrmfe" && request.tenant == "<go_id>" && span.kind == "server"`; 11 labels |
| `mdrm-cdm-widevine` | CDM – Widevine | `tenantId`, `service == "widevine-license-generator"`, `operation == "/wvpl/:version/GetLicense"` |
| `mdrm-cdm-fairplay` | CDM – FairPlay | `tenantId`, `service == "fairplay-license-generator"`, `operation == "/MDRM/FPLS/:version/GetLicense"` |
| `mdrm-cdm-playready` | CDM – PlayReady | `tenantId`, `service == "playready"`, `operation == "/playready/rightsmanager.asmx"` |
| `mdrm-lrm` | License chain status – LRM | `tenantId`, `service == "license-request-manager"`; `group_by ["fcId","deviceId","http.status_code"], sum` |

Verbatim queries as run on 2026-10-31 (`<id>` is the tenant value from `resolve_tenant.py`; LX-2 turns the literals into placeholders):

```
# ctap  (EU, project from the resolver)
spans count | delta
| filter http.route == "/ctap/:uxApiVersion/devices/me/playsessions"
| group_by ["http.user_agent", "lightstep.trace_id"], sum

# smvod + smvod-ts  (EU)
spans count | delta
| filter (service == "sm-linear" || service == "sm-vod")
    && session.api == "SetupSession" && span.kind == "server"
| group_by ["householdId", "deviceId", "session.clientIp", "sessionId", "contentId",
            "externalPackageId", "lightstep.trace_id", "playbackURL"], sum

# mdrmfe  (EU)
spans count | delta
| filter service == "go-mdrmfe" && request.tenant == "<go_id>" && span.kind == "server"
| group_by ["drmAuthToken.sessionId", "fcid", "drmAuthToken.householdId", "drmAuthToken.deviceId",
            "drmAuthToken.deviceType", "drmAuthToken.drmType", "drmAuthToken.brRef",
            "request.contentId", "http.status_code", "http.user_agent", "http.client_ip"], sum

# mdrm-cdm-widevine  (US)
spans count | delta
| filter ("tenantId" == "<id>") && ("service" == "widevine-license-generator")
    && (operation == "/wvpl/:version/GetLicense")
| group_by ["fcId", "http.status_code", "drmInfo.DeviceType", "drmInfo.Make", "drmInfo.Model",
            "drmInfo.Platform", "drmInfo.SecurityLevel"], sum

# mdrm-cdm-fairplay  (US)
spans count | delta
| filter ("tenantId" == "<id>") && ("service" == "fairplay-license-generator")
    && (operation == "/MDRM/FPLS/:version/GetLicense")
| group_by ["fcId", "http.status_code", "FP_SPC_contents"], sum

# mdrm-cdm-playready  (US)
spans count | delta
| filter ("tenantId" == "<id>") && ("service" == "playready")
    && (operation == "/playready/rightsmanager.asmx")
| group_by ["fcId", "http.status_code", "drmInfo.deviceType", "drmInfo.manufacturerName",
            "drmInfo.modelName"], sum

# mdrm-lrm  (US)
spans count | delta
| filter ("tenantId" == "<id>") && ("service" == "license-request-manager")
| group_by ["fcId", "deviceId", "http.status_code"], sum
```

For the shared-project tenants (ZM, GH), `ctap` adds `&& sessionInfo.busUnitId == "<go_id>"` and the same attribute in the `group_by`; `smvod` does the same with plain `busUnitId`.

## Decisions (2026-10-31)

- **Tenant attribute is per kind, in the registry:** `ctap` uses `sessionInfo.busUnitId` and `smvod` uses `busUnitId`, both only when `shared_project` is true (ZM, GH). ZA is a dedicated project and
  gets neither the clause nor the column. `mdrmfe` always filters `request.tenant`; the mDRM kinds always filter `tenantId`. Values come from `resolve_tenant.py`, never from the script.
- **GH CDM queries:** the GH notebook's Widevine, FairPlay and PlayReady charts lack the `operation == ...` clause that ZA and ZM have. Owner decision: GH must use the same `operation` filter as ZA
  and ZM, so there is one template per kind and no per-tenant override. The GH notebook itself is out of date; fixing it is optional and not part of this story.
- **`smvod` and `smvod-ts` come from one chart:** the aggregates table gives `smvod.csv` and the span-samples table gives `smvod-ts.csv`. The span samples (with `oldest_micros`, `youngest_micros`,
  `duration_millis`) may not be reachable through `query_timeseries`; LX-1 must test this first and mark `smvod-ts` go or no-go.
- **Safety check kept for shared tenants:** if the resolver says the tenant is shared and the output lacks the `busUnitId` column, or has more than one distinct value, the script fails instead of
  writing the file.
- **Window (2026-10-31):** one full UTC day per run, `<date>T00:00:00Z` to `<date>T23:59:59Z` (e.g. 2026-10-29 00:00 to 23:59 UTC). The earlier 12:00-to-11:59 wording is superseded.
- **Cron-ready:** unattended, non-interactive, no prompts, token from the environment or root `.env`; exit code 0 only on full success and non-zero on any failure, so cron can alert. It supports a
  default date of "yesterday UTC" when `--date` is omitted, and `--force` for reruns; reruns are idempotent (existing files are skipped without `--force`).
- **Logging contract (`docs/refactor/logging-and-correlation-id.md`):** `init_logging("export-lightstep-day")` once at the entry point (one FCID per run, minted nowhere else, logs to the project logs
  directory). Run start `INFO` with tenant, date and kinds; external-call start `DEBUG` with a query fingerprint and `redact_params` (never the token or raw query text); success `INFO` with
  `duration_ms`, row count and slice count; failure logged once via `logger.exception` in the layer that first catches it; run end `INFO` with a per-kind success/failure summary.
- **Design rules (`docs/refactor/`):** the HTTP client is injected (DIP) as a `Protocol` so tests use a fake with no network; the kind registry is a plain `dict` (no Factory class); the client,
  slicer, CSV writer and CLI are separate single-responsibility modules; a small per-module exception hierarchy (no `None` for failure, no broad `except`); type hints on all public functions,
  keyword-only args beyond three, `ruff`/`mypy` clean, no `Any` outside the JSON boundary.
- **Why the first attempts returned nothing:** `busUnitId == "dtunf6yo"` was applied on the dedicated ZA project, where that attribute does not exist.

---

## LX-1 — Feasibility spike

**Files to change / create:**
- `scratch/` stub per `scratch/SCRATCH.md` — throwaway probe code lives here, not in `scripts/`.
- `docs/plan/lightstep-daily-export-automation/stories.md` — record the findings under this task.

**What to implement:**

1. For one hand-exported day (ZA, 2026-10-29), run each of the eight kinds from "Known queries" through the API for the same UTC day, sliced to stay under the 50-series cap. Start with the `smvod-ts`
   span samples: if they cannot be reached through `query_timeseries` (or another public endpoint), mark `smvod-ts` no-go before doing anything else.
2. Per kind, diff the API result against the hand file: row count, column set, key coverage. Note whether table-style charts (all attribute columns, e.g. `playbackURL`) can be reproduced with
   `group_by`.
3. Measure request latency, rate limiting and the largest slice that does not truncate for each kind.
4. Record go / no-go per kind and the exact UQL that reproduced it. Ask the user for any notebook query that is not in the repo.

**Tests (no network, no real external services):** none — exploratory; findings are the deliverable.

**Commit:** `docs(lightstep): record export API feasibility spike`

---

## LX-2 — Query templates and per-kind registry

**Files to change / create:**
- `queries/lightstep/<slug>.md` — one parameterised template per kind (`{{tenant_filter}}`, `{{oldest}}`, `{{youngest}}` placeholders), following `docs/guides/query-catalog.md`.
- `queries/lightstep/index.md` — rows for the new templates.
- `scripts/lib/lightstep_export_kinds.py` — registry: kind → template slug, project system, output suffix, expected columns.
- `tests/` — registry tests.

**What to implement:**

1. Add the eight templates using the UQL proven in LX-1; no literal ids, dates or tenants. `smvod` and `smvod-ts` share one template and differ only in the output (aggregates vs span samples).
2. Build the registry as data, not branching code, so a ninth kind is one new entry. Each entry names its tenant attribute and whether it applies always or only on a shared project.
3. Resolve the project and shared-project filter through the `resolve_tenant.py` logic, never hardcoded.
4. Use the ZA/ZM `operation` filter for the three CDM kinds for every tenant, including GH.

**Tests (no network, no real external services):**
- `test_registry_covers_all_eight_kinds` — every kind has template, system and suffix.
- `test_unknown_kind_raises` — a missing kind fails loudly.
- `test_dedicated_tenant_has_no_busunitid` — the expanded ctap and smvod queries for ZA contain no `busUnitId` text.
- `test_shared_tenant_uses_kind_specific_attribute` — ZM/GH ctap uses `sessionInfo.busUnitId` and smvod uses `busUnitId`.
- `test_cdm_queries_identical_across_tenants` — apart from the tenant id, GH's CDM queries equal ZA's.

**Commit:** `feat(lightstep): add export query templates and kind registry`

---

## LX-3 — Lightstep API client

**Files to change / create:**
- `scripts/lib/lightstep_api.py` — `query_timeseries(...)`, `split_window(...)`, `fetch_all_series(...)`; HTTP injected so tests need no network.
- `tests/` — client tests with a fake transport.

**What to implement:**

1. Read the token from `LIGHTSTEP_API_KEY_EU` / `LIGHTSTEP_API_KEY_US` in the environment, falling back to the gitignored root `.env`; fail with a clear message if missing; never log it.
2. Slice a window into fixed-size sub-windows; when a response reports `series_returned == 50` and `series_total > 50`, halve that slice and retry until it fits or hits a minimum width, then fail.
3. Retry transient errors (429/5xx) with backoff; surface everything else.
4. Deduplicate a series seen in adjacent slices by label set and timestamp, and verify the merged count against each slice's `series_total`.

**Tests (no network, no real external services):**
- `test_split_halves_on_truncation` — a capped response triggers a halved retry.
- `test_missing_token_raises` — no env var, no call.
- `test_dedupe_across_slices` — boundary series counted once.
- `test_min_width_truncation_fails` — unsplittable slice raises rather than returning partial data.

**Commit:** `feat(lightstep): add API client with truncation-aware slicing`

---

## LX-4 — UI-format CSV writer

**Files to change / create:**
- `scripts/lib/lightstep_csv.py` — series → rows, UTF-8 BOM, all fields quoted, UI column order; part-file naming `<date>_<NN>_<kind>.csv`.
- `tests/` — writer tests including a golden sample taken from an existing hand-exported file.

**What to implement:**

1. Map each kind's group labels to its columns and the `min/max/avg/sum/value` tail exactly as the UI writes them.
2. Name files `<date>_<kind>.csv`, switching to numbered parts only when a kind has to be split, matching `combine_lightstep_parts.py` conventions.
3. Write atomically (temp file then rename) and refuse to overwrite an existing file without `--force`.

**Tests (no network, no real external services):**
- `test_header_and_quoting_match_golden` — output equals the golden structure.
- `test_existing_file_not_overwritten` — second write without `--force` raises.

**Commit:** `feat(lightstep): write exports in UI CSV format`

---

## LX-5 — `export_lightstep_day.py` CLI

**Files to change / create:**
- `investigations/ctap-smvod/scripts/export_lightstep_day.py` — thin `main()` composing the libs above.
- `tests/` — CLI wiring test with a fake client.

**What to implement:**

1. Arguments via `argparse`: `--tenant`, `--date` (default yesterday UTC), `--kinds` (default all eight), `--output-dir`, `--force`; no hardcoded ids or paths.
2. Call `init_logging()` once, resolve the tenant, compute the UTC-day window (00:00:00Z to 23:59:59Z), fetch and write each kind, and follow the logging contract in the Decisions section.
3. Continue with the remaining kinds if one fails, then finish by running the existing input check for the tenant/date; exit non-zero if any kind or the check failed.
4. Document a sample crontab line in `docs/usage.md` (absolute paths, `.env` loading, log location) in LX-6.
5. Skip kinds that need an unregistered mDRM tenant with a clear message instead of guessing.

**Tests (no network, no real external services):**
- `test_default_date_is_yesterday_utc` and `test_one_failed_kind_continues_and_exits_nonzero`.
- `test_log_lines_carry_one_fcid_and_no_token` — captured logs share one FCID and never contain the token.
- `test_all_kinds_written_for_tenant_date` — fake client yields eight files.
- `test_failed_input_check_exits_nonzero` — a FAIL finding sets the exit code.

**Commit:** `feat(ctap-smvod): add one-command daily Lightstep export`

---

## LX-6 — Docs, registry and parity run

**Files to change / create:**
- `investigations/ctap-smvod/docs/usage.md` — document the command next to the manual export rule.
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — point to the script as the default path; keep the manual steps as fallback.
- `SCRIPTS.md` (workspace root) — add entries for the new scripts.
- `CONTEXT.md` — "What Exists" line for the new command.

**What to implement:**

1. Run the command for ZA 2026-10-29 into a scratch directory and compare with the hand-exported files; record row-count parity and any known differences.
2. Document token setup (`.env`, never committed) and the rate-limit behaviour measured in LX-1.

**Tests (no network, no real external services):** none — documentation and a recorded parity run.

**Commit:** `docs(lightstep): document daily export command and parity run`

---

## LX-7 — Cron-ready daily pipeline wrapper

Added 2026-10-31. Once the export works, the downstream commands for the same day must also run from cron, in this order (dates are `DDMMYYYY`; example 29102026 = 2026-10-29):

```
python3 scripts/check_lightstep_inputs.py --date 29102026 --drm
python scripts/run_pipeline.py --date 29102026 --drm --skip-input-check
python scripts/extract_error_report_1xxx.py --date 29102026
for t in ZA GH ZM; do python scripts/rank_households_by_error.py --csv output/$t/2026-10-29_error_report_1xxx.csv --top 10; done
```

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_daily_pipeline.py` — thin `main()` that runs export, input check, `run_pipeline`, error-report extraction and per-tenant ranking for one UTC date.
- `tests/` — orchestration test with a fake step runner.

**What to implement:**

1. Arguments via `argparse`: `--date` (default yesterday UTC), `--tenants` (default ZA,GH,ZM), `--skip-export`; `init_logging("run-daily-pipeline")` once, one FCID for the whole run.
2. Run each step as a subprocess with an argument list (no `shell=True`), passing the FCID through the environment (cross-process propagation is flagged as deferred in the logging doc; this is its
   first consumer). Log step start, duration and exit code once each.
3. Stop at the first failed step except the per-tenant ranking, which continues for the remaining tenants; exit non-zero if any step failed. Verify each expected output CSV exists afterwards.
4. Known risk: `run_pipeline.py` steps 3 and 4 use Athena through AWS SSO, which expires; cron needs a non-interactive credential path or a clear fail-fast on an expired SSO session. Resolve this in
   the task, do not assume.
5. Document the crontab line in `docs/usage.md`.

**Tests (no network, no real external services):**
- `test_steps_run_in_order_with_date_argument` and `test_failed_step_stops_pipeline_and_exits_nonzero`.
- `test_ranking_continues_across_tenants_after_one_failure`.

**Commit:** `feat(ctap-smvod): add cron-ready daily pipeline wrapper`
