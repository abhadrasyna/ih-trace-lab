# Lightstep daily export automation — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

The eight kinds and their sources (from `investigations/ctap-smvod/docs/lightstep-drm-exports.md` and `docs/usage.md`):

| Kind (file suffix) | Project / region | Tenant system | Notes |
|---|---|---|---|
| `ctap` | GO project, EU | `lightstep_go` | Columns `http.user_agent`, `lightstep.trace_id`, `min/max/avg/sum/value`; `sessionInfo.busUnitId` filter on shared projects. |
| `smvod` | GO project, EU | `lightstep_go` | `householdId`, `deviceId`, `sessionId`, `lightstep.trace_id`; `busUnitId` filter on shared projects. |
| `smvod-ts` | GO project, EU | `lightstep_go` | `sessionId`, `oldest_micros`, `youngest_micros`; must cover the whole UTC day. |
| `mdrmfe` | GO project, EU | `lightstep_go` | `go-mdrmfe` license by session; `span.kind == "server"`. |
| `mdrm-cdm-widevine`, `mdrm-cdm-fairplay`, `mdrm-cdm-playready`, `mdrm-lrm` | `mcs-mdrm-production`, US | `lightstep_mdrm` | Filtered to the mDRM-internal tenant id; needs the US API token. |

Auth: org API token from `LIGHTSTEP_API_KEY_EU` / `LIGHTSTEP_API_KEY_US` (environment or gitignored `.env`). Endpoint verified 2026-10-31: `POST
https://api.<region>.lightstep.com/public/v0.2/<org>/projects/<project>/telemetry/query_timeseries`.

---

## LX-1 — Feasibility spike

**Files to change / create:**
- `scratch/` stub per `scratch/SCRATCH.md` — throwaway probe code lives here, not in `scripts/`.
- `docs/plan/lightstep-daily-export-automation/stories.md` — record the findings under this task.

**What to implement:**

1. For one hand-exported day (ZA, 2026-10-29), pick the saved UQL/notebook chart for each of the eight kinds and run it through the API for the same UTC day, sliced to stay under the 50-series cap.
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

1. Add the eight templates using the UQL proven in LX-1; no literal ids, dates or tenants.
2. Build the registry as data, not branching code, so a ninth kind is one new entry.
3. Resolve the project and shared-project filter through the `resolve_tenant.py` logic, never hardcoded.

**Tests (no network, no real external services):**
- `test_registry_covers_all_eight_kinds` — every kind has template, system and suffix.
- `test_unknown_kind_raises` — a missing kind fails loudly.

**Commit:** `feat(lightstep): add export query templates and kind registry`

---

## LX-3 — Lightstep API client

**Files to change / create:**
- `scripts/lib/lightstep_api.py` — `query_timeseries(...)`, `split_window(...)`, `fetch_all_series(...)`; HTTP injected so tests need no network.
- `tests/` — client tests with a fake transport.

**What to implement:**

1. Read the token from the environment only; fail with a clear message if missing; never log it.
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

1. Arguments via `argparse`: `--tenant`, `--date`, `--kinds` (default all eight), `--output-dir`, `--force`; no hardcoded ids or paths.
2. Resolve the tenant, compute the UTC-day window (00:00–24:00), fetch and write each kind, and log per-kind row counts and slice counts with `setup_logging()`.
3. Finish by running the existing input check for the tenant/date and exit non-zero on any FAIL.
4. Skip kinds that need an unregistered mDRM tenant with a clear message instead of guessing.

**Tests (no network, no real external services):**
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
