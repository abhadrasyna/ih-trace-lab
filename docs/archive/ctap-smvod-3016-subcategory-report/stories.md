# Daily 3016 sub-category report (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> add one line to your backlog/session-log file.

All code lives inside `investigations/ctap-smvod/`. Scripts are thin `argparse` CLIs over pure functions; no hidden file or network I/O in the logic functions; a crash beats a silently wrong result.

---

## SUB-1 — Sub-category rules

**Files to change / create:**
- `investigations/ctap-smvod/scripts/classify_3016_subcategory.py` — `classify(row) -> str`, `PRIORITY` map.
- `investigations/ctap-smvod/tests/test_classify_3016_subcategory.py`.

**What to implement:** first match wins, on the flat-file columns `errorcode`, `pipeline_status`, `media_error_type`:

| Order | Condition | Sub-category | Priority |
|---|---|---|---|
| 1 | `errorcode` in 3014, 3015 | MSE append failed (3014/3015) | P3 |
| 2 | `pipeline_status` contains "reinitialization failed" | Video decoder re-initialisation failed | P2 |
| 3 | `media_error_type` is 4 and `pipeline_status` empty | No data / source not supported | P2 |
| 4 | `pipeline_status` contains "audio" or "disconnected" | Audio decode / pipeline disconnected | P3 |
| 5 | `pipeline_status` contains "decode" (includes "Media failed to decode") | Video decode error | P1 |
| 6 | anything else | Uncategorised | P? |

**Tests (no network):**
- `test_each_known_status_maps_to_expected_subcategory` — one row per rule, including the `PipelineStatus::` prefix and no-prefix variants.
- `test_unknown_status_is_uncategorised_not_dropped`.

**Commit:** `feat(ctap-smvod): add 3016 sub-category rules`

---

## SUB-2 — Events builder

**Files to change / create:**
- `investigations/ctap-smvod/scripts/build_3016_subcategory_events.py` — `build_events(errors, setup, pos, opco, date)`.
- `investigations/ctap-smvod/tests/test_build_3016_subcategory_events.py`.

**What to implement:**
1. Input rows: flat-file rows with `errorcode` in 3014/3015/3016. Join `*_setupsession_with_outcome.csv` and `*_position_report.csv` by `sessionId`, first row per session; skip empty `sessionId` on
   both sides.
2. Columns: `date, opco, subcategory, errorcode, datetime, householdId, deviceId, sessionId, content_uuid, externalPackageId, segment_file, event_position, player_phase, pipeline_status, browser,
   device_model, os, user_agent, session_max_position, join_setup, join_position, hh_repeat_events, content_distinct_hh`.
3. `user_agent` is the raw string from the flat file. `browser`/`device_model` are parsed (Edge, Opera, Firefox, Samsung Internet, Chrome/CriOS, Safari; iPhone/iPad/Macintosh as iOS/Mac; Android model
   from the UA, else "android (model unknown)").
4. `content_uuid`: setupsession, else position report, else parsed from the 3014/3015 segment URL (`/vod[ec]/<uuid>/<n>/<file>`); `segment_file` from the same URL.
5. `hh_repeat_events` and `content_distinct_hh` ignore empty `householdId`.

**Tests:**
- `test_join_by_session_adds_content_and_keeps_raw_user_agent`.
- `test_empty_session_or_household_never_joins_or_counts`.
- `test_segment_url_parsed_for_vode_and_vodc`.

**Commit:** `feat(ctap-smvod): add 3016 sub-category events builder`

---

## SUB-3 — Summary builder

**Files to change / create:**
- `investigations/ctap-smvod/scripts/build_3016_subcategory_summary.py` — `build_summary(events)`.
- `investigations/ctap-smvod/tests/test_build_3016_subcategory_summary.py`.

**What to implement:** group events by `(opco, subcategory)`; output `date, opco, subcategory, events, households, sessions, priority`. Households and sessions are distinct and exclude empty ids.
Sub-categories with no events are omitted.

**Tests:**
- `test_counts_events_distinct_households_and_sessions`.
- `test_summary_event_total_equals_events_rows`.

**Commit:** `feat(ctap-smvod): add 3016 sub-category summary builder`

---

## SUB-4 — Daily CLI

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_3016_subcategory_report.py` — args `--opco`, `--date` (or `--from/--to`), `--base`, `--out`.
- `investigations/ctap-smvod/tests/test_run_3016_subcategory_report.py`.

**What to implement:**
1. Read `output/<OPCO>/error_eventdata_flat/<date>_all.csv` (missing file → exit with a clear error, never an empty report).
2. Write `output/<OPCO>/subcategory_3016/<date>_subcategory_summary.csv` and `<date>_subcategory_events.csv`.
3. Reconcile: events rows must equal the 3014/3015/3016 rows in the flat file, else raise. Missing setupsession/position files warn on stderr and leave the `join_*` columns false.
4. Date range loops the same logic per day; `init_logging()` per project convention.

**Tests:** `test_writes_both_csvs_for_fixture_day`, `test_missing_flat_file_fails_loudly`, `test_reconciliation_mismatch_raises`.

**Commit:** `feat(ctap-smvod): add daily 3016 sub-category report CLI`

---

## SUB-5 — Docs and registry

**Files to change / create:**
- `investigations/ctap-smvod/docs/usage.md` — command, inputs, the two output files, the rules table.
- `SCRIPTS.md` (via `python scripts/dev/generate_scripts_registry.py`) and `CONTEXT.md` "What Exists".
- `scratch/2026-10-24_ctap_smvod_3016_subcategory_sample.py` and `scratch/2026-10-24_3016_sample_out/` — remove, or mark superseded by the new script.

**Tests:** none (docs only); confirm the registry lists the new scripts.

**Commit:** `docs(ctap-smvod): document 3016 sub-category report`
