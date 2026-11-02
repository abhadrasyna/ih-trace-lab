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

### LX-1 findings (2026-11-01, ZA 2026-10-29, probe `scratch/2026-11-01_lightstep_export_api_feasibility_probe.py`)

Request body: `{"data":{"attributes":{"query":<UQL>,"query-type":"default","oldest-time":<RFC3339 Z>,"youngest-time":<RFC3339 Z>,"output-period":<seconds = window>,"include-exemplars":false}}}`;
response `data.attributes.series[]` with `group-labels` (`"name=value"` strings) and `points`. An empty window returns no `series` key. Auth header `Authorization: bearer <token>`.

Per kind, full UTC day, 1 h slices halved on >=50 series, keyed on the group-by columns (min/max/avg/sum/value ignored). `both` = keys present in API and hand files:

| Kind | API keys | Hand keys | Both | Only API | Only hand | Calls | Verdict |
|---|---|---|---|---|---|---|---|
| ctap | 5865 | 5829 | 5829 | 36 | 0 | 322 | **GO** (superset) |
| smvod | 5864 | 5830 | 5719 | 145 | 111 | 320 | **GO** (see quirks) |
| mdrmfe | 3684 | 3656 | 3593 | 91 | 63 | 204 | **GO** (see quirks) |
| mdrm-cdm-widevine | 2962 | 2979 | 2941 | 21 | 38 | 148 | **GO** (see quirks) |
| mdrm-cdm-fairplay | 514 | 563 | 511 | 3 | 52 | 26 | **GO** (see quirks) |
| mdrm-cdm-playready | 117 | 114 | 114 | 3 | 0 | 24 | **GO** (superset) |
| mdrm-lrm | 3595 | 3656 | 3567 | 28 | 89 | 202 | **GO** (see quirks) |
| smvod-ts | — | — | — | — | — | — | **GO, derived (approximate)**, no public span-sample endpoint |

- **`smvod-ts`:** `query_spans`, `query_span_samples`, `spans/query`, `query_traces` under `/telemetry/` (and `/spans/query`) all return HTTP 403 with an empty body, so the public API exposes no
  span-sample endpoint to this token. The hand file is a 500-row sample per hour part, not a complete set. **Decision (2026-11-01): derive it approximately** from the `smvod` series' point timestamps
  (first and last non-zero point per `sessionId`, `output-period` 1 s), keeping the validator's UTC-day coverage satisfied.
- **Derivation probe (`scratch/2026-11-01_lightstep_smvod-ts_derive_probe.py`, ZA 2026-10-29, 328 calls, about 14 min):** every one of the 3,492 sessions in the hand `smvod-ts` was found (3,492 /
  3,492); the API also returned 2,347 sessions the hand sample lacks, which is expected because the hand file is capped at 500 rows per hour. Timestamps do not match exactly: `oldest_micros` derived
  minus hand has median -3.5 s (min -46,043 s, max +6.5 s) with only 229 / 3,492 within 1 s; `youngest_micros` has median +10.5 s (max +19,371 s) with 3 / 3,492 within 1 s. The large outliers are most
  likely sessions with several spans (the hand row is one span, the derivation merges all spans of a session); the median offsets suggest Lightstep returns coarser buckets than 1 s. Neither cause is
  confirmed. `duration_millis` (hand median 33.6 ms) cannot be derived from point timestamps. So the derived file is session-level coverage only: `error_flag`, `component_name`, `span_name` and
  `duration_millis` need placeholders or extra `group_by` labels, and LX-2 must check what `check_lightstep_inputs.py` and the downstream steps actually read from `smvod-ts` before choosing them.
- **Retention:** the API returns no data for 2026-10-02 to 2026-10-24 and data from 2026-10-26, so retention is about 7 days. The daily export must run within a week of the UTC day, and the 2026-09-28
  hand file cannot be reproduced. Any parity run must use a day within the last 7 days.
- **Differences are small (about 1-3 % of keys) and explained by:** (1) the UI export prefixes values that start with `-` with an apostrophe (`'-QSn81...`, in `householdId`; 13 rows in one smvod part)
  — the writer must reproduce or the diff must normalise it; (2) the hand exports were taken at a different time than the API run, so late-arriving spans and hour-boundary assignment differ; (3) blank
  vs missing attribute values (`drmInfo.Make=` empty in hand rows). Exact normalisation is LX-6's parity-run job, not a blocker.
- **Latency / limits:** p50 1.0-1.3 s, max 3.5 s per call; no 429 or 5xx in ~1,250 calls, run with six kinds in parallel. One `IncompleteRead` on a large smvod response, so the client needs retries on
  network errors. Full-day cost: ctap 322 calls, smvod 320, mdrmfe 204, widevine 148, lrm 202, fairplay 26, playready 24 (about 20 minutes of wall time per kind sequentially for the heaviest).
- **Largest slice:** 1 h always fit under the cap after halving; `ctap`, `smvod` and `mdrmfe` need halving down to a few minutes at peak hours because `lightstep.trace_id`/`sessionId` make each span
  its own series. Start slices at 1 h and rely on auto-split.
- **`mdrmfe` tenant value:** `request.tenant` for ZA equals the GO project id fragment `iye9omdf`; LX-2 must take it from the resolver/`config/tenants.yaml`, not parse the project name.
- **Table-style charts:** all attribute columns (including `playbackURL`, `FP_SPC_contents`) are reproducible with `group_by`.

---

## LX-2 — Query templates and per-kind registry

**Files to change / create:**
- `queries/lightstep/<slug>.md` — one parameterised template per kind (`{{tenant_filter}}`, `{{oldest}}`, `{{youngest}}` placeholders), following `docs/guides/query-catalog.md`.
- `queries/lightstep/index.md` — rows for the new templates.
- `scripts/lib/lightstep_export_kinds.py` — registry: kind → template slug, project system, output suffix, expected columns.
- `tests/` — registry tests.

**What to implement:**

1. Add the templates using the UQL proven in LX-1; no literal ids, dates or tenants. `smvod-ts` is derived (LX-1 decision 2026-11-01): it reuses the `smvod` query at `output-period` 1 s and takes each
   session's first and last non-zero point as `oldest_micros`/`youngest_micros`; registry entry kind `derived` with the columns it can fill. First check which `smvod-ts` columns the validator and the
   downstream steps read, and fill the rest with documented placeholders. For `mdrmfe`, `request.tenant` comes from `config/tenants.yaml` (the GO tenant id), not from the project name.
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
2. Slice a window into fixed-size sub-windows (start at 1 h); the API response has only a `series` array (no `series_total`), so when `len(series) >= 50` halve that slice and retry until it fits or
   hits a minimum width, then fail. An empty window has no `series` key and must be treated as zero series.
3. Retry transient errors (429/5xx and network errors such as `IncompleteRead`) with backoff and a retry cap; surface everything else. Measured in LX-1: no 429 or 5xx in about 1,250 calls.
4. Deduplicate a series seen in adjacent slices by label set and timestamp (merge points, do not drop the second slice's points); there is no `series_total` to cross-check, so verify by re-querying a
   sample slice at a smaller width.

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

## LX-8 — SOLID refactor of the export CLI

Added 2026-11-01. Must be done before LX-9, LX-6 and LX-7. Review of LX-5 against `docs/refactor/design-principles.md` and `code-review-checklist.md` found these violations; fix all of them with no
behaviour change.

**Files to change / create:**
- `investigations/ctap-smvod/scripts/export_lightstep_day.py` — keep only argument parsing and wiring in `main()`.
- `scripts/lib/lightstep_export_kinds.py` — add a row-builder field to `KindSpec`.
- `scripts/lib/lightstep_export_runner.py` (new) — the per-kind pipeline and the run loop, with injected dependencies.
- `scripts/lib/lightstep_csv.py` — make `parse_labels` public; `lightstep_smvod_ts.py` imports it.
- `investigations/ctap-smvod/tests/test_export_lightstep_day.py` and `tests/lib/` — update tests.

**What to implement (one finding each):**

1. **S:** split `export_kind` into small steps (skip check, fetch, tenant safety check, build rows, write) and keep it as orchestration only.
2. **O:** the registry entry names its row builder (`build_rows` or `derive_rows`); the CLI has no `derived_from` branch.
3. **O:** the "tenant has no mDRM id" skip rule moves from the CLI into the registry (a per-kind `is_available(tenant)` rule), so a new kind or rule needs no CLI edit.
4. **D:** inject a `TokenProvider` (a `Protocol` with one method per region) in place of `load_token` and the shared `tokens` dict; inject the target resolver the same way.
5. **D:** `main()` is the only composition root; remove the `transport or ...` and `input_check or ...` fallbacks from the callable signatures, and give tests their own wiring.
6. **S:** separate result reporting (console lines) and the "does the input check apply" policy from the run loop.
7. **Coupling:** no cross-module import of a private name.

**Tests (no network):** the existing CLI tests keep passing unchanged in behaviour; add one test that a new registry entry with its own row builder and availability rule works with no CLI change.

**Commit:** `refactor(ctap-smvod): split Lightstep export CLI per design principles`

---

## LX-9 — Incremental export: part files, stitching, resume, per-step logging

Added 2026-11-01. Must be done before LX-6 and LX-7, after LX-8. A full day is 6-20 minutes per kind with no output until the kind ends, and a failure late in a kind loses everything.

**Split into four sub-tasks (2026-11-01)** because the combined diff was about 900 lines. Do them in order, one commit each; 9a and 9b leave the CLI behaving as today. The numbered spec below stays
the single source of truth; each sub-task implements the items listed here, and "LX-9" elsewhere means all four.

- **LX-9a** — the pure merge and part reader that item 3 relies on: dedupe by label set, recompute `min/max/avg/sum` across parts, read a part file back into rows.
  - Files: `scripts/lib/lightstep_stitch.py` (new), `scripts/lib/lightstep_csv.py`, tests in `tests/lib/`.
  - Commit: `feat(lightstep): add part-series stitch and part reader`
- **LX-9b** — items 1 and 2: per-window part files, manifest (window, kind, fingerprint, row count, sha256), verified resume, `--fresh`, `--part-hours`, reused/remaining log line.
  - Files: `scripts/lib/lightstep_export_runner.py`, `export_lightstep_day.py`, tests.
  - Commit: `feat(lightstep): write resumable part files`
- **LX-9c** — items 3, 4 and 5: stitch per kind, `smvod-ts` from stitched `smvod` parts, sanity checks (a)-(d), delete only the `<TENANT>_<date>/` subfolder.
  - Files: runner, tests.
  - Commit: `feat(lightstep): stitch parts and clean up after checks`
- **LX-9d** — item 6: per-step INFO lines with ETA under one FCID, opt-in `init_logging(..., log_dir=, file_prefix=, date=, keep_days=)`, `--log-dir`, 7-day prune of own files only.
  - Files: `src/lib/logging/bootstrap.py`, runner, CLI, tests.
  - Commit: `feat(logging): per-date export log files with pruning`

Tests listed at the end of the spec belong to the sub-task that implements the behaviour; the worker-side FCID/no-token test belongs to LX-9d.

**LX-9b design decision (2026-11-01):** part files hold the raw fetched series as JSON (`scripts/lib/lightstep_parts.py`, `<kind>_<NN>.json` plus `<kind>_<NN>.manifest.json`), not UI-format CSV.
Points are kept, so `stitch_series` is exact (no count sidecar or approximate `avg` needed) and `smvod-ts` can be derived after stitching. The runner already stitches the parts into the output file;
LX-9c adds the sanity checks and cleanup, and the CSV-row stitch from LX-9a stays available for those checks.

**Files to change / create:**
- `scripts/lib/lightstep_export_runner.py` — fetch per window into part files, resume, stitch.
- `scripts/lib/lightstep_stitch.py` (new) — pure merge of part series; recomputes `min/max/avg/sum` across parts.
- `scripts/lib/lightstep_csv.py` — read a part file back into rows.
- `investigations/ctap-smvod/scripts/export_lightstep_day.py` — new flags only.
- Tests in `tests/lib/` and `investigations/ctap-smvod/tests/`.

**What to implement:**

1. **Part files:** fetch fixed windows (`--part-hours`, default 1) and write each to its own file as soon as it is fetched (atomic writer). Parts go in
   `/Users/abhadra/myWork/myOffice/ih-trace-lab/tmp/lightstep-export/<TENANT>_<date>/` (a subfolder, relative to the repo root; `tmp/` itself holds a tracked `README.md` and is never deleted).
2. **Resume (`--resume`, on by default; `--fresh` discards the parts folder and starts over):** after any failure or interruption, rerunning the same tenant, date and kinds continues from the parts
   already downloaded and fetches only the missing windows. Each part gets a small manifest entry (window, kind, query fingerprint, row count, sha256) written after the part file; a part is reused
   only if the file exists, its sha256 and row count match the manifest, and the query fingerprint matches the current query (so a changed query or tenant never reuses stale parts). A part that fails
   this check is logged and fetched again. The log says how many parts were reused and how many remain.
3. **Stitch:** when every part of a kind exists, merge them into `<output-dir>/<date>_<kind>.csv` (deduplicated by label set, stats recomputed across parts).
4. **`smvod-ts` is derived from the stitched `smvod` parts** (first and last non-zero point per session across the whole day), not per part; its own parts are fetched at the 1 s period, then stitched
   before deriving.
5. **Sanity check, then cleanup:** the parts folder is deleted only after every check below passes; any failure keeps it so the rerun can resume. Checks: (a) every expected window of every kind has a
   verified part (no gaps, no duplicates); (b) the stitched file has the expected header and BOM, and its row count equals the number of distinct label sets across the parts; (c) each stitched file
   was written and re-read successfully; (d) for the core kinds the Step 0 input check passes on the output folder. Then delete only the `tmp/lightstep-export/<TENANT>_<date>/` subfolder, and log what
   was deleted.
6. **Logging (`docs/refactor/logging-and-correlation-id.md`):** one INFO line per step, all under the single FCID: `part 3/24 window=... series=... calls=... duration_ms=...`, `stitching kind=...
   parts=24 rows=...`, `kind done elapsed=...`, an ETA estimate per kind, and `cleanup tmp=...`.
   - **Log files:** by default this command writes its log to `investigations/ctap-smvod/logs/export-lightstep-day_<YYYY-MM-DD>.log`, where the date is the `--date` data day (arguments are parsed
     before logging starts). On start it deletes its own `export-lightstep-day_*.log` files whose filename date is more than 7 days before today, never the current run's file and never other files
     (such as the pipeline's `DDMMYYYY.txt`). It is opt-in on the shared bootstrap (`init_logging(..., log_dir=, file_prefix=, date=, keep_days=)`), so no other entry point changes; the shared
     `logs/app.log` default is untouched. Console (stderr) output stays on, and `--log-dir` overrides the folder.
   - **Tests** use a temp folder: the file is named by the `--date` day, files older than 7 days are pruned, newer and unrelated files and the current file are kept, and a second run for the same date
     appends. **Tests (no network):**
- A failure at part N leaves parts 1 to N-1 and a rerun fetches only the rest.
- A corrupted or truncated part, or one with a different query fingerprint, is re-fetched on resume; `--fresh` ignores all parts.
- A missing window or a row-count mismatch at the sanity check blocks the stitch and the cleanup, and the parts folder is kept.
- Stitched output equals the one-shot output for the same fake data.
- Derived `smvod-ts` from stitched parts equals the one-shot derivation.
- Parts are deleted after success and kept after failure; `tmp/README.md` is never touched.
- Worker-side log lines carry the FCID and never the token (explicit test per the checklist).

**Commit:** `feat(lightstep): export in resumable part files`

---

## LX-10 — Parallel fetch of part windows

Added 2026-11-01, split out of LX-9. Must be done after LX-9 (it needs independent part windows) and before LX-6 and LX-7. A full day currently fetches windows one after another; threads cut the wall
time because each call waits on the network.

**Files to change / create:**
- `scripts/lib/lightstep_parallel.py` (new) — runs a list of independent jobs with a bounded worker pool and returns results in input order.
- `scripts/lib/lightstep_export_runner.py` — hand the window jobs to that runner; no thread code inside it.
- `investigations/ctap-smvod/scripts/export_lightstep_day.py` — new `--workers` flag only.
- Tests in `tests/lib/` and `investigations/ctap-smvod/tests/`.

**Design (checked against `docs/refactor/design-principles.md` and `code-review-checklist.md`):**
- **SRP:** the pool lives in its own module; the runner decides which windows to fetch, the pool decides how to run them, and neither knows about the other's internals.
- **DIP / OCP:** the runner receives the executor-like runner as an injected argument (default: the thread pool, tests pass a serial one), so serial and parallel runs share one code path and a process
  pool or async version could be added without editing the runner.
- **Context (`logging-and-correlation-id.md`):** each job runs inside `contextvars.copy_context()` so the FCID is kept in worker threads. This is the known gotcha and has its own test.
- **Thread safety:** workers only fetch and write their own part file (atomic writer, distinct names). The manifest is written by the collecting thread alone, so no shared mutable state or locks.
  Progress and ETA logs are emitted from the collecting thread, not the workers.
- **Failure:** the first failed window stops new submissions, in-flight windows finish and are kept for resume, and the run exits non-zero. Retries and backoff stay per call in the API client.
- **Limits:** `--workers` default 4, hard cap 8, `--workers 1` is the serial path. LX-1 measured no throttling at six parallel kinds; a 429 or throttling response is logged and counted, and the README
  note says to lower `--workers` if it appears.
- **Output ordering:** results are returned in input order, so the stitched files are identical regardless of worker count.

**Tests (no network):**
- A parallel run returns the same rows and stitched files as `--workers 1`.
- Worker-side log lines carry the FCID and never the token (explicit test per checklist section 4).
- A failing window stops new submissions, completed parts are kept, and a rerun resumes.
- `--workers` above the cap or below 1 is rejected.
- The runner works with an injected serial runner (no threads started).

**Commit:** `feat(lightstep): fetch part windows in parallel with bounded workers`

---

## LX-6a — Parity run against a hand-exported day

Split from LX-6 on 2026-11-02 and moved first: the 2026-10-29 hand export leaves the 7-day Lightstep retention window about 5 Nov, after which no parity run is possible.

**Files to change / create:** a short findings note in `investigations/ctap-smvod/docs/` (for example `2026-11-xx-lightstep-export-parity.md`); no code.

**What to implement:** run the command for ZA on a UTC day within the last 7 days into a scratch directory and compare with the hand-exported files by key set, not row count: key-level differences of
up to about 3 % in either direction were seen in LX-1 (export timing, late spans). Record the tolerance and any known differences, including the leading-apostrophe values and the approximate
`smvod-ts`.

**Tests (no network, no real external services):** none — a recorded parity run.

**Commit:** `docs(lightstep): record daily export parity run`

---

## LX-6b — Docs and registry

Split from LX-6 on 2026-11-02 and moved last so it documents the final wrapper, log layout and health check once.

**Files to change / create:**
- `investigations/ctap-smvod/docs/usage.md` — document the command next to the manual export rule, the daily wrapper (§7g) and the health check.
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — point to the script as the default path; keep the manual steps as fallback.
- `SCRIPTS.md` (workspace root) — add entries for the new scripts and shared `lib` modules.
- `CONTEXT.md` — "What Exists" line for the new command.

**What to implement:** document token setup (`.env`, never committed), the 7-day retention limit, the rate-limit behaviour measured in LX-1 (about 1.0-1.3 s per call, no throttling; 24-322 calls per
kind per day) and the LX-6a parity result.

**Tests (no network, no real external services):** none — documentation.

**Commit:** `docs(lightstep): document daily export, wrapper and health check`

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

---

## LX-13 — Past-month debug table through the pipeline and the daily wrapper

Added 2026-11-02, done the same day. After the month rolled over, the unsuffixed debug-events table no longer held October, so the 2026-10-30 pull returned near-empty data for ZA (debug_states 362
rows against about 55,000 on a normal day; error_eventdata 10 against about 2,500), GH (56 and 13) and ZM (header only), and the household ranking had 5 rows. Re-pulling needs the month-suffixed table
`<id>_ccl_debug_events_<suffix>` (for example `oct26`; the September table was `sept26`, so the suffix cannot be derived from the date).

**What was implemented (three commits):**
1. `dc4539e` and `10e494c` — `add_table_suffix_arg(parser)` in `scripts/lib/tenant_context.py` (one shared option; `resolve_tenant_context(..., table_suffix=)` already validated it). Used by
   `run_pipeline.py` (passed only to Step 4 `run_athena_debug_events.py` and Step 6f `run_athena_error_eventdata.py`; Step 3 reads unified sessions and does not get it), the two Athena scripts and
   `run_athena_debug_sessions.py`. A bad suffix fails at `run_pipeline` start before any step runs. Test stubs of `resolve_tenant_context` accept the new keyword.
2. `3690f57` — `run_daily_pipeline.py` gets `--table-suffix` and `--force`, passed to the `run_pipeline` step only and echoed in the resume line; a warning is logged when the run date is not in the
   current UTC month and no suffix was given. The suffix is an explicit flag, not derived, because month-table names are irregular and a wrong guess fails quietly.

**Re-run for a past month (all tenants; `--force` is needed because the output CSV names carry no suffix and a non-empty CSV is otherwise reused):**

```
python3 run_daily_pipeline.py --date 30102026 --skip-export --table-suffix oct26 --force
```

**Tests:** `test_build_steps_forwards_table_suffix_only_to_debug_table_steps` (`test_run_pipeline.py`), `test_add_table_suffix_arg_parses_and_defaults_to_none` (`test_tenant_context.py`),
`test_table_suffix_and_force_reach_only_run_pipeline_step` (`test_run_daily_pipeline.py`).

**Open follow-up:** confirm the `oct26` table exists for GH and ZM (read-only `SHOW TABLES`) before relying on the re-run for those tenants.

---

## LX-11 — Daily wrapper streams step output live

Added 2026-11-02. In `logs/run-daily-pipeline_2026-10-30.log` the line `step start: run_pipeline` (12:54:46) was followed by nothing for about 5 minutes 20 seconds, then every line of that step's
output appeared at once at 13:00:07, so the run looked hung. Cause: `make_subprocess_runner` in `run_daily_pipeline.py` starts each step with `stdout=PIPE` and calls `proc.communicate(timeout=...)`,
which returns only when the step exits, and `run_steps` logs the captured lines afterwards. The child's own timestamps are preserved, so nothing is lost; the log is just not live. `run_pipeline.py`
runs many Athena steps for three tenants, so a long quiet gap is normal and must be told apart from a real hang.

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_daily_pipeline.py` — the runner and `run_steps`.
- `investigations/ctap-smvod/tests/test_run_daily_pipeline.py` — runner and streaming tests.
- `investigations/ctap-smvod/docs/usage.md` — section 7g note.

**What to implement:**

1. Replace `communicate()` with a loop that reads `proc.stdout` line by line and logs each line at once as `[<step name>] <line>` (same format as today), while keeping every line so the runner's
   return value `(exit code, combined output)` is unchanged. Move the per-line logging into the runner via an optional `on_line` callback so `run_steps` no longer logs the lines a second time; a fake
   runner in tests that returns the output without calling `on_line` must still get its lines logged (keep a fallback in `run_steps`, or give the fake runner the callback).
2. Keep the timeout: a watchdog (`threading.Timer`) that calls `os.killpg(proc.pid, SIGKILL)` after `timeout_seconds`, then the read loop ends on EOF; the result is exit 124 with the output plus
   `timed out after <N>s`, as today. The process still runs in its own session so Athena and `aws-sso` children die with it.
3. Heartbeat: if no line arrives for 60 seconds, log `step still running: <name> (<elapsed>s)` at INFO and repeat every 60 seconds until output resumes or the step ends. A small constant, no new flag;
   read on a thread or with `selectors` so the heartbeat fires while the read blocks.
4. Child output must reach the pipe promptly: pass `PYTHONUNBUFFERED=1` in the step environment (the `FCID` env is already added in `main`), otherwise the child buffers and streaming gains little.
5. Mention the live-streaming and heartbeat behaviour in `docs/usage.md` section 7g.

**Tests (no network, no real external services; use small real subprocesses such as `python -c`):**
- `test_lines_are_logged_before_the_step_exits` (a child that prints, sleeps, prints: the first line is logged before the child ends).
- `test_timeout_kills_process_group_and_returns_124` (output so far is kept, exit code 124).
- `test_returned_output_and_exit_code_unchanged_for_fast_step`.
- `test_heartbeat_logged_for_quiet_step` (heartbeat interval injected as a small value).

**Risks:** the watchdog and heartbeat threads must not outlive the step or leak on timeout; read order of stderr and stdout stays interleaved because stderr is merged into stdout.

**Decisions (open, default in brackets):** heartbeat interval [60 s]; live lines go to both console and the log file [yes, the logger already does both].

**Commit:** `feat(ctap-smvod): stream daily-pipeline step output live with heartbeat`

---

## LX-12 — Per-script dated log files by default

Added 2026-11-02. `run_daily_pipeline.py` already writes `investigations/ctap-smvod/logs/run-daily-pipeline_<date>.log` (`init_logging(..., log_dir=, file_prefix=, date=, keep_days=)`), but the other
60 or so `ctap-smvod` entry points call `init_logging("<slug>")` with no log arguments, so they append to the shared `logs/app.log` at the repo root. Wanted: by default, each script writes
`<investigation>/logs/<prefix>_<date>.log`, the same format as the wrapper.

**Revised 2026-11-02:** retention is the shared `DEFAULT_LOG_KEEP_DAYS = 7` in `src/lib/logging` (added in SPR-2; `init_logging` uses it when `keep_days` is not given), not a per-script number; the
helper below passes no `keep_days` of its own. Needs SPR-2.

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/runtime.py` (or a new small `scripts/lib/script_logging.py`) — `init_script_logging(slug)`.
- Every `investigations/ctap-smvod/scripts/*.py` that calls `init_logging(` — one mechanical replacement, no other change.
- `.gitignore` — add `investigations/ctap-smvod/logs/*.log` (the existing `logs/*.log` rule only covers the repo-root folder).
- `investigations/ctap-smvod/tests/` — wrapper test.
- `investigations/ctap-smvod/docs/usage.md` — short note on where logs go.

**What to implement:**

1. `init_script_logging(slug, *, date=None, keep_days=...)` calls `init_logging(slug, log_dir=<investigation>/logs, file_prefix=<prefix>, date=<date>, keep_days=<N>)`; the log folder is built from the
   repo path, never hardcoded. Returns the FCID like `init_logging`.
2. Replace the direct `init_logging(...)` calls in `ctap-smvod/scripts` with it (all entry points; check `src/lib/logging` is not edited).
3. The daily wrapper keeps its own `run-daily-pipeline_<date>.log` and its steps become separate files, one per script and day (for example `run_pipeline_2026-11-02.log`); there is no single per-run
   file because the wrapper runs each step as a subprocess.
4. After this task `app.log` no longer receives these scripts' logs; say so in `docs/usage.md`.

**Tests:** `test_init_script_logging_builds_dated_path_under_investigation_logs`, `test_init_script_logging_passes_prune_days`, and one test that the entry-point scripts import the wrapper (a
grep-style guard so a new script cannot silently go back to `app.log`).

**Decisions (open, to confirm before starting):** prefix is the full slug (`ctap-smvod-run_pipeline`) or the short script name; date is UTC (matches the FCID timestamp) or local; prune after how many
days (the wrapper uses 30, export uses 7) or keep everything; only `ctap-smvod` or reusable for other investigations.

**Commit:** `feat(ctap-smvod): write per-script dated log files by default`

## LX-18 — Daily pipeline health check and failure notification

**Revised 2026-11-02 (needs SPR-6):** do not parse the log text. The daily wrapper writes the SPR-2 status file (via LX-19) and `check_status` from `src/lib/pipeline_runtime/health.py` finds
FAILED/NOT RUN steps and a missing or stale run. Drop `scripts/lib/run_summary.py`; this task keeps `notify.py` (notifier, `logs/alerts.log`, optional webhook), the FCID dedupe, the WARNING digest
(the only part that still reads the log) and the cron lines. `check_daily_pipeline_health.py` becomes a thin wrapper over `scripts/check_pipeline_health.py`'s core.

Added 2026-11-02. `run_daily_pipeline.py` exits non-zero and ends its log with a `==== run summary ====` block (OK / FAILED / NOT RUN per step), but nothing reads either, and cron does not catch up
missed runs, so failures go unnoticed. The 31 Oct log holds about 50 WARNING lines (TransportError retries, smvod-release sanity checks) that are not all failures.

**Files to change / create:**
- `scripts/lib/run_summary.py` — pure parser: summary block and WARNING class counts from log text.
- `scripts/lib/notify.py` — notifier interface (stdout/macOS + `logs/alerts.log`; optional webhook via env var, never in the repo).
- `scripts/check_daily_pipeline_health.py` — argparse (`--date`, `--log-dir`, `--notify`); exit 1 on failure or missing log; dedupe per FCID.
- `investigations/ctap-smvod/tests/` — parser, notifier (no network) and dedupe tests.
- `docs/usage.md` §7g (cron lines: after the run, plus a ~15:00 IST dead-man's-switch), `CONTEXT.md`, `/Users/abhadra/github_copilot/SCRIPTS.md`.

**What to implement:** alert on FAILED/NOT RUN steps or a missing/incomplete log; warnings only as a digest line; verify against the 30/31 Oct logs.

**Decisions (open):** notification channel (Teams webhook recommended); warning threshold (suggest none: alert on FAILED only).

**Commit:** `feat(ctap-smvod): alert on daily pipeline failures`

---

## LX-14 — Derive `--table-suffix` for a past-month day

Added 2026-11-02. The 2026-10-31 run read the unsuffixed debug table and gave 5 GH 1xxx rows against 177 after a `--table-suffix oct26 --force` rerun; LX-13 only logs a warning.

**Files to change / create:** `scripts/lib/tenant_context.py` (the shared suffix helper), `run_daily_pipeline.py`, `investigations/ctap-smvod/tests/test_run_daily_pipeline.py`, `docs/usage.md` §7g.

**What to implement:** one pure function maps a day outside the current UTC month to its suffix (`oct26`); the wrapper passes it to `run_pipeline` automatically, or exits 1 before any step when the
suffix table is unknown or not derivable. An explicit `--table-suffix` still wins.

**Tests:** `test_past_month_day_derives_suffix`, `test_current_month_day_has_no_suffix`, `test_explicit_suffix_wins`, `test_underivable_month_fails_fast`.

**Commit:** `fix(ctap-smvod): derive table suffix for past-month daily runs`

---

## LX-15 — Tenant-aware `smvod-ts` coverage check

Added 2026-11-02. A quiet tenant (ZM: 133 sessions, first span 04:17 UTC) fails the `smvod-ts` UTC-day coverage check in the export and in `check_lightstep_inputs.py`, and the legend does not say
whether a FAIL blocks the pipeline.

**Files to change / create:** `scripts/lib/lightstep_inputs.py`, `check_lightstep_inputs.py`, the export's input check, tests, `docs/usage.md`.

**What to implement:** a per-tenant coverage tolerance (start/end gap allowed, from a small config next to the tenant list, not hardcoded in the check); the legend states which result codes block the
pipeline and which are advisory. One shared helper serves both callers.

**Tests:** a low-volume tenant passes with a late first span; a normal tenant with the same gap fails; the legend text matches the blocking behaviour.

**Commit:** `fix(ctap-smvod): tenant-aware smvod-ts coverage tolerance`

---

## LX-16 — Quiet skip for an existing export kind

Added 2026-11-02. Re-running over an existing `smvod-release` file logs about 24 per-part "missing or failed verification" sanity warnings and may leave stale temp parts.

**Files to change / create:** the export runner module in `scripts/lib/` and its tests.

**What to implement:** when the final file for a kind already exists, log one skip line and return before the per-part sanity check; remove stale temp parts; `--fresh` still re-fetches.

**Tests:** `test_existing_kind_logs_one_skip_line`, `test_no_part_warnings_for_existing_kind`, `test_fresh_refetches`.

**Commit:** `fix(ctap-smvod): skip existing export kinds quietly`

---

## LX-19 — Daily wrapper step identity and module split

**Revised 2026-11-02 (needs SPR-2):** `StepRunner`, `make_subprocess_runner`, `run_steps` and the status/summary types are no longer created here: they move to `src/lib/pipeline_runtime/` in SPR-2
(`Step` becomes `Unit`). This task keeps what is wrapper-specific: `Unit.id`/`group`/`tenant` assigned in the plan, `scripts/lib/daily_plan.py` (pure `build_steps`, `coverage_plan`,
`select_from_step`), `scripts/lib/daily_summary.py` (the human-readable run-summary block, resume command from parsed args), and calling the shared `run_units`. `daily_runner.py` is not created. The
design-review gate is satisfied by SPR-1's `design.md`.

Added 2026-11-02 from the `run_daily_pipeline.py` review (`docs/refactor/design-principles.md`: SRP, DIP). `STEP_GROUPS` resumes by name prefix, so renaming a step silently breaks `--from-step`;
`main()` rebuilds the resume flags by hand and can drift from `parse_args`; planning, running and summary share one 300-line file.

**Process:** a design review of the seam (a short `Protocol` for the runner and the step-plan shape, "before" diagram per `docs/refactor/architecture-diagrams.md`) is committed and approved before any
code changes; no behaviour change.

**Files to change / create:** `scripts/run_daily_pipeline.py` (thin `main()`), new `scripts/lib/daily_plan.py` (pure `build_steps`, `coverage_plan`, `select_from_step`), `scripts/lib/daily_runner.py`
(`StepRunner` Protocol, subprocess runner, `run_steps`), `scripts/lib/daily_summary.py` (pure `format_summary`), existing tests updated to the new import paths.

**What to implement:** `Step` gains `id`, `group` and `tenant`; `select_from_step` and `format_summary` use `group`; the resume command is built from one function of the parsed args (the old
hand-built flag string goes away); no log or exit-code change.

**Tests:** the existing suite passes unchanged apart from imports; add `test_renaming_a_step_does_not_break_resume` and `test_resume_flags_round_trip_through_parse_args`.

**Risks:** FCID and env handling must stay in `main`; import cycles between the new modules (dependency direction: plan and summary have no imports of the runner).

**Reuse constraint (added 2026-11-02 from the SOLID review):** `daily_runner.py` and `Step` must not depend on anything wrapper-specific, because LX-22 reuses them in `run_pipeline.py`. The "run
steps, log, verify outputs, continue or stop" loop is the Template Method; the runner stays an injected function type (Strategy), and steps stay a plain table, not a class hierarchy.

**Commit:** `refactor(ctap-smvod): split daily wrapper into plan, runner and summary`

---

## LX-17 — Resume only failed tenants, one interpreter, legend once

Added 2026-11-02. After LX-19 (needs `Step.tenant`). The resume hint re-runs every tenant, steps may use different interpreters, and the check-inputs table and legend print once per step.

**Files to change / create:** `scripts/lib/daily_summary.py`, `scripts/lib/daily_plan.py`, `run_daily_pipeline.py`, `check_lightstep_inputs.py`, tests, `docs/usage.md` §7g.

**What to implement:** the resume command carries `--tenants <failed tenants>` (all when a tenant-less step failed); every step argv uses the repo `.venv` interpreter, resolved once; the check-inputs
table and legend are logged once per run.

**Tests:** `test_resume_names_only_failed_tenants`, `test_all_steps_use_pinned_interpreter`, `test_legend_logged_once`.

**Commit:** `feat(ctap-smvod): tenant-scoped resume hint and pinned interpreter`

---

## LX-20 — Drop the duplicate 1xxx extract and isolate tenant failures

Added 2026-11-02 from the wrapper review. `run_pipeline.py` Step 6e (`extract_error_report_1xxx_6xxx.py`) and the wrapper's `extract_error_report_1xxx.py` may overlap, and one tenant's failure
currently stops all remaining steps.

**Process:** start with a read-only audit (`docs/refactor/code-deduplication-and-taxonomy.md` Step 1): compare the two scripts' columns, filters and outputs and write the result in the task commit.
Remove the wrapper step only if the outputs match; otherwise record why both stay.

**Files to change / create:** `scripts/lib/daily_plan.py`, `scripts/lib/daily_runner.py`, tests, `docs/usage.md` §7g.

**What to implement:** per-tenant steps after the shared export/check are marked tenant-scoped and continue past another tenant's failure; the summary and exit code still report every failure; steps
that consume all tenants stay all-or-nothing.

**Tests:** `test_failed_tenant_does_not_skip_other_tenants`, `test_summary_reports_failed_tenant`, plus a test for whichever dedupe outcome the audit decided.

**Commit:** `refactor(ctap-smvod): dedupe 1xxx extract and isolate tenant failures`

---

## LX-24 — Single SSO pre-flight and gated DRM exports

**Revised 2026-11-02 (needs SPR-3):** the once-per-run pre-flight is `Preflight` in `src/lib/pipeline_runtime/`, with the refresh injected from `scripts/lib/runtime.ensure_valid_credentials`; this
task wires it into the wrapper and `run_pipeline.py`, adds `--skip-auth-check` to every Athena child, and does the DRM-kind gating (the DRM part is unchanged).

Added 2026-11-02 from the Lightstep/Athena call review. Each `run_athena_*` script runs its own SSO check and refresh unless `--skip-auth-check` is passed, so a run repeats the check per script and
tenant (and races under LX-21). The DRM Lightstep exports run even when the DRM reports are skipped.

**Files to change / create:** `scripts/run_pipeline.py` (or the shared runner after LX-22), `scripts/run_daily_pipeline.py`, the DRM kind selection in `scripts/export_lightstep_day.py`, tests,
`docs/usage.md` §7g.

**What to implement:** one pre-flight refresh at the start of the run (reusing the existing `aws_sso` helper), then `--skip-auth-check` on every child; a failed refresh still fails fast with the same
message. `--skip-drm-reports` also drops the DRM kinds (`mdrmfe`, the CDM kinds, `lrm`) from the wrapper's export step.

**Tests:** `test_children_get_skip_auth_check_after_preflight`, `test_failed_preflight_stops_before_any_step`, `test_skip_drm_reports_drops_drm_export_kinds`.

**Commit:** `feat(ctap-smvod): single SSO pre-flight and gated DRM exports`

---

## LX-25 — Adaptive Lightstep window sizing and early skip

Added 2026-11-02. A window that hits the 50-series cap is split, so each truncation costs the failed call plus the split calls (24 to 322 calls per kind per day, about 1.0 to 1.3 s each). The
part-hours are fixed today.

**Files to change / create:** the export planner/runner in `scripts/lib/`, a small per-tenant stats file under `data/lightstep/<TENANT>/` (gitignored), tests, `docs/usage.md`.

**What to implement:** after each export, record per kind the call count and truncated-window count; the next run derives its starting window size from the latest stats (clamped to a sane range;
`--part-hours` still wins). Check for a finished final file before building any client or making any call. Output must equal the fixed-window run.

**Tests:** `test_window_shrinks_after_truncation`, `test_window_grows_when_no_truncation`, `test_explicit_part_hours_wins`, `test_finished_day_makes_no_api_call`.

**Commit:** `feat(lightstep): size export windows from previous run statistics`

---

## LX-26 — Spike: shared Lightstep fetch for ZM and GH

Added 2026-11-02. ZM and GH share one Lightstep project and their `ctap`/`smvod` queries differ only by the `busUnitId` filter, so one query grouped by `busUnitId` could serve both and roughly halve
their calls.

**Process:** a scratch spike per `scratch/SCRATCH.md` (duplicate-check first), no change to the exporter. Compare call counts, truncation rate and the key sets against the per-tenant exports for one
day.

**Go criteria (to confirm before starting):** call reduction of at least 30 %, key-set difference within the LX-1 tolerance (about 3 %), and no new truncation that the splitter cannot resolve. If met,
add an implementation task; if not, record why and close.

**Commit:** `docs(lightstep): record shared ZM/GH fetch spike result`

---

## LX-23 — One debug-events extract per tenant-day

Added 2026-11-02. Step 4 (`run_athena_debug_events`) and Step 6f (`run_athena_error_eventdata`), and on investigation days `run_athena_session_bandwidth` and `run_athena_debug_sessions`, each scan
`ccl_debug_events` for the same tenant and day and each run `json_extract_scalar` over every row. Step 3 (`run_athena_playback_outcome`) and `run_athena_session_ingest` both query `unified_sessions`.
Step 4 also builds a large `IN (...)` list of session ids from the Lightstep merge.

**Process:** a read-only audit first (`docs/refactor/code-deduplication-and-taxonomy.md` Step 1): list the columns, event ids and filters each of the five scripts uses, measure bytes scanned per query
from Athena's execution stats, and write the result before designing the shared extract. Follow `docs/guides/query-catalog.md` for any new SQL.

**Files to change / create:** a new catalog query and `scripts/run_athena_debug_extract.py` (one day, one tenant, flattened columns, written under `data/athena/<TENANT>/`), `scripts/lib/` reader
helpers, the steps above reading the extract, tests, `docs/usage.md`.

**What to implement:** produce the daily extract once (cached by tenant, day, table suffix and query version; `--force` re-pulls); Steps 4 and 6f read and filter it locally and keep their current
output files and columns; join on session ids locally instead of an `IN` list; combine the Step 3 and ingest queries into one.

**Tests:** same rows as before for a fixture day, cache hit makes no query, `--force` re-pulls, table-suffix change invalidates the cache. No network.

**Risks:** extract size (the error events alone are 10 to 15 MB per day); keep only the event ids needed. Do after LX-24.

**Commit:** `feat(ctap-smvod): share one Athena debug-events extract per tenant-day`

---

## LX-27 — Artifact registry and prune script

**Revised 2026-11-02 (needs SPR-5):** the registry type, `plan_prune`/`apply_prune` and `scripts/prune_artifacts.py` come from SPR-5; do not write `scripts/lib/artifact_registry.py` or a second prune
script. This task does the grep-verified audit, the ctap-smvod registry module (`Artifact` rows for `data/` and `output/`, plus `docs/artifact-registry.md` as the human view), `RETENTION.md`, and the
`parts pruned only after the stitched file exists` rule as a registry condition.

Added 2026-11-02 from the data/output review. `data/` is 672 MB and `output/` is 533 MB (both gitignored). Duplicates seen: Lightstep part files (138 MB) kept beside the stitched files (267 MB),
`smvod-ts` (95 MB) used only to enrich the merge, `error_eventdata_flat/` (265 MB, `*_all.csv` plus per-error-code copies, on top of the raw Athena file), the `setupsession` intermediate (59 MB),
`check_script/` and `parallel_version/` folders under `data/lightstep/ZA/` (13 MB each), and one-off investigation outputs (bandwidth, ingest, `debug_all_events`, 3xxx household files, the range
reports).

**Files to change / create:** `investigations/ctap-smvod/docs/artifact-registry.md` (artifact pattern, producer, readers, keep-or-prune, retention days), `scripts/lib/artifact_registry.py` (pure
parser and age rules), `scripts/prune_artifacts.py` (argparse, dry run by default, `--apply`), `SCRIPTS.md` entries, tests, `RETENTION.md` for this investigation.

**What to implement:** build the registry from the `scripts/` readers (grep-verified, not guessed); mark unused or superseded artifacts; the prune script lists, then with `--apply` deletes only
registry rows marked prunable and older than their retention, never anything without a row. Keep `ad hoc` outputs in an `adhoc/` folder going forward.

**Tests:** `test_unregistered_file_is_never_deleted`, `test_dry_run_deletes_nothing`, `test_retention_age_rule`, `test_parts_pruned_only_after_stitched_file_exists`.

**Risks:** deleting data a later analysis still reads; the registry's reader column is the safeguard. Run after LX-23 so the retained set is final.

**Commit:** `feat(ctap-smvod): add artifact registry and prune script`

---

## LX-21 — (optional) Parallel per-tenant chains

**Revised 2026-11-02 (needs SPR-4):** the bounded pool, ordering, failure isolation and Athena cap are `run_pool` from SPR-4 (it absorbs `scripts/lib/lightstep_parallel.py`). This task adds
`--parallel-tenants N`, the concurrency-safety check for `run_pipeline --tenant T`, and the tenant log prefix.

Added 2026-11-02. Tenants are independent after the shared steps, so wall-clock time can drop by running them concurrently. Do only after LX-19, LX-20 and LX-24 (single SSO refresh), and only if a
serial run is too slow.

**Process:** first confirm `run_pipeline --tenant T` is safe to run concurrently (shared output files, `aws-sso` refresh races, Athena quota) and record it; if not safe, close the task as not done.

**What to implement:** `--parallel-tenants N` (default 1) runs per-tenant chains in a bounded `ThreadPoolExecutor` behind the injected runner; a semaphore caps concurrent Athena-using steps; one SSO
refresh happens before the fan-out; log lines carry the FCID and a tenant prefix.

**Tests:** same results as the serial run with a fake runner, one tenant failing leaves the others complete, FCID present in worker log lines, the Athena cap is respected.

**Commit:** `feat(ctap-smvod): optional parallel tenant chains in daily wrapper`

---

## LX-22 — `run_pipeline.py` adopts the shared runner and typed steps

**Revised 2026-11-02 (needs SPR-2):** the shared runner is `src/lib/pipeline_runtime/runner.py` (no rename step; `daily_runner.py` never existed). Express `_build_steps` as `Unit`s and `_run_tenant`
as `run_units` with an injected runner whose default keeps today's `subprocess.run` behaviour (no timeout, output inherited); the Step 1b post-check hangs off the unit id.

Added 2026-11-02 from the SOLID/pattern review. `run_pipeline._run_tenant` runs a list of `(label, argv, skip)` tuples with a direct `subprocess.run` (DIP seam missing, no timeout, no output capture)
while `run_daily_pipeline.py` has its own runner; Step 1b's post-check is keyed on `step_index == 0`. Do after LX-19 (the shared runner and `Step`) and LX-20.

**Files to change / create:** `scripts/run_pipeline.py`, `scripts/lib/daily_runner.py` (rename to a neutral name such as `step_runner.py` if LX-19 left a wrapper-specific one),
`investigations/ctap-smvod/tests/` (existing `run_pipeline` tests plus new ones), `docs/usage.md`.

**What to implement:** `_build_steps` returns typed `Step` entries (id, argv, skip, post-check); `_run_tenant` calls the shared runner, injected for tests; Step 1b's input check is a post-check on its
step id; the printed `==> [tenant] label` / `$ command` lines and SKIPPED lines stay as they are; flags, outputs and exit codes do not change.

**Tests:** `test_run_tenant_uses_injected_runner`, `test_step_1b_postcheck_runs_after_step_by_id`, `test_skipped_steps_are_not_run`, `test_failed_step_returns_failure_description`; existing tests pass
unchanged.

**Risks:** the daily wrapper's timeout/streaming behaviour (LX-11) must not leak into the per-tenant run unless asked for; keep the runner's defaults equal to today's `subprocess.run` behaviour for
`run_pipeline.py`.

**Commit:** `refactor(ctap-smvod): run_pipeline uses shared step runner and typed steps`
