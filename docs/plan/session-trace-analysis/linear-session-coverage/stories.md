# Linear session coverage (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

This file is a starting spec and will be appended to as findings come in.

---

## LC-1 — Updated Lightstep export queries

**Files to change / create:**
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — add the corrected smvod query (the one in `prompt.md`) as a template with a `<busUnitId>` placeholder, plus a short table of known tenants
  (ZM `dtunf6yo`, GH `apbyfj9d`) pointing at `config/tenants.yaml` as the source of truth; no tenant is special-cased.
- `investigations/ctap-smvod/docs/usage.md` — note the export now carries both services and that the file keeps the `_smvod.csv` name for now.

**What to implement:**

1. Resolve a tenant with `scripts/resolve_tenant.py --system lightstep_go --tenant <code>` (shown for ZM and GH) and record the project plus filter pattern in the doc.
2. Give the matching smvod-ts (span-samples) query with `service in (sm-vod, sm-linear)`; the current ts export has no linear rows.
3. State that old exports are VOD-only, lack `http.status_code`, and are not backfilled; re-exporting is a manual step done only after this story is implemented.
4. Add `"http.status_code"` to the `group_by` of the smvod query. Reason: a SetupSession that fails before a session exists (ZA 2026-10-24: 5 rows HTTP 403, 1 row HTTP 500) has a blank `sessionId`,
   `playbackURL` and `externalPackageId`, and the `error` tag stays `0`, so nothing in the CSV tells these failures apart from a bad export.

**Tests:** docs only, none.

**Commit:** `docs(ctap-smvod): include sm-linear in export queries`

---

## LC-2 — Merge: `session_type` and linear-safe content key

**Files to change / create:**
- `investigations/ctap-smvod/scripts/merge_ctap_smvod_csv.py` — add a `session_type` output field derived from the `sessionId` prefix (`abr-vod-` / `abr-linear-`, else `unknown`); for linear, set a
  channel key from `playbackURL`/`contentId` instead of the blank `content_uuid`.
- `investigations/ctap-smvod/tests/` — a merge test with a linear fixture row and the status-code fixtures below.

**What to implement:**

1. Reuse `session_kind` from `scripts/lib/drm_funnel.py` (import, do not re-implement) for the prefix rule.
2. Add `session_type` to `OUTPUT_FIELDS` and populate it for every row. 2a. Add `http.status_code` to `SMVOD_FIELDS` as an optional input column: an old export without it merges unchanged with a blank
   value, and no error is raised. Add a derived `setup_failed` flag (blank `sessionId` with a non-2xx status) so pre-session failures can be counted separately from real sessions.
3. Make sure a linear smvod row with empty `externalPackageId` still matches its CTAP trace and is not emitted as `ctap_only`.

**Tests (no network, no real external services):**
- `test_linear_row_matches_ctap_and_has_session_type` — linear fixture is `matched` with `session_type == "linear"`.
- `test_blank_external_package_id_not_error` — empty `externalPackageId` does not change the match status.
- `test_status_code_column_carried` — a 403 row with blank `sessionId` keeps `http.status_code == "403"` and `setup_failed` set; a 200 row does not.
- `test_old_export_without_status_column_merges` — an export without `http.status_code` merges with a blank value and no error.

**Commit:** `feat(ctap-smvod): add session_type and linear key to merge`

---

## LC-3 — Downstream audit and fixes

**Files to change / create:**
- `investigations/ctap-smvod/scripts/build_3016_subcategory_events.py`, `correlate_cdn_ips.py`, `extract_position_report.py`, `extract_error_report_1xxx_6xxx.py`, `run_pipeline.py`,
  `summarize_pipeline_run.py` — audit each for VOD assumptions (`/vod[a-z]/` regexes, `content_uuid`, `externalPackageId`, the `smvod` naming).
- Matching tests.

**What to implement:**

1. For each script, record in this file whether it is fixed or documented VOD-only (and why).
2. Add per-`session_type` counts to `summarize_pipeline_run.py`.
3. Keep VOD output unchanged (compare a VOD-only day before and after).

**Tests:** one happy-path and one edge-case test per changed public function.

**Commit:** `fix(ctap-smvod): handle linear sessions downstream`

---

## LC-4 — Validate and close out

**Files to change / create:**
- `investigations/ctap-smvod/docs/` — a short validation note for re-exported ZM and GH days and a VOD-only day; answers to the open questions in `prompt.md`.
- `CONTEXT.md` — "What Exists" entry for linear coverage.

**What to implement:**

1. Run `run_pipeline.py --tenant <code>` for each tenant with linear (ZM, GH) and for a VOD-only tenant day; confirm no linear `ctap_only` rows, sensible `session_type` counts, and identical VOD
   output.
2. Grep scripts and tests for hardcoded tenant codes/ids introduced by this story; there must be none (fixtures use placeholder ids).
2. Check Athena playback-outcome coverage of linear and record the result.
3. Re-run a VOD-only date and confirm identical output to before.

**Tests:** run the existing ctap-smvod test suite; it must be green.

**Commit:** `docs(ctap-smvod): record linear coverage validation`
