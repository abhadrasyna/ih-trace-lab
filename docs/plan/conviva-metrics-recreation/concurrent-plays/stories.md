# Concurrent Plays — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: scratch work is exempt from the test gate until graduation (CMR-CP-6); verify by running on the saved data and recording the output. Confirm scope and plan with the user before creating or
editing anything (project Steps 2-3).

**Build rule (user, 2026-10-27):** the scratch POC only validates that the metric is possible. Every formal script and helper the story needs is built while working the tasks, as tested code, not left
for the end and not run through MCP. Code specific to this story lives in `investigations/conviva-metrics/`, common code in `src/lib/` (user, 2026-10-27). Before writing anything new, check for an
existing script or helper to enhance (for example `run_athena_debug_sessions.py`, `scripts/lib/runtime.py`, `flatten_debug_events.py`, `scripts/lib/debug_event_parser.py`); move shared logic into a
helper instead of copying it. When the story is done the full set of scripts, helpers, queries and tests exists. CMR-CP-6 then graduates the POC logic, report writer and renderer.

---

## CMR-CP-1 — Settle the definition points and decide the report content

**Files:** this story's `prompt.md` (definition section), the existing report `2026-10-24_ZA_concurrent-plays-report.md` (rewritten to the agreed sections), and the `../discussion-prompt.md`
Discussion log.

**What to settle with the user (discussion, no code):**

1. The end rule for a playing interval with no closing event (last event, last event plus a timeout, or Conviva's inactivity limit if the user can obtain it). The POC peak is 16 under both rules.
2. Whether `PLAYER_SEEK`, `PLAYER_EOF` and `PLAYER_ERROR` close playing time, and the tie rule for events with the same timestamp (the POC sorts closing events before `PLAYING`).
3. A Conviva Concurrent Plays figure for ZA on 2026-10-24 (summary and 15-minute series) to compare against, and the tolerance that counts as a match.
4. UTC versus local day boundary, and the bucket alignment (minute buckets from 00:00 UTC).
5. The sections the supporting report must contain. The user said this is decided in the next session; do not assume the POC sections are final.

**Settled (2026-10-27, with the user):**

1. Open intervals end at the session's last event; the timeout is an argument (300 s as a check).
2. `PLAYER_SEEK`, `PLAYER_EOF` and `PLAYER_ERROR` close playing time; closing events sort before `PLAYING` on equal timestamps.
3. No Conviva reference figure exists, so no match is claimed and no tolerance is set.
4. UTC day, minute buckets from 00:00 UTC (Conviva's reporting timezone stays an assumption).
5. Report content, accepted on the ZA 2026-10-24 output, kept short: tables and the chart with a one- or two-line summary, no local file references. Sections: definition; headline with the chart; top
   10 content by played sessions (columns Content, Played sessions, % of played, Households, plus a Not resolved row); device breakdown at the peak minute (device class / OS / browser from the parsed
   user agent, DRM device type, each with an Unresolved row); playback type at the peak minute. Sensitivity, reconciliation, known gaps and reproduction are not in the report. Playback type is
   currently taken from the session-id prefix (`abr-vod-`); the raw `contenttype` in `eventdata` is the proper source (CMR-CP-5).

**Commit:** `docs(conviva-metrics): cmr-cp-1`

---

## CMR-CP-2 — Download the full-day raw debug events

**Files:** the new investigation folder `investigations/conviva-metrics/` (scaffold it with `scripts/dev/scaffold_investigation.py`; classify per `docs/guides/project-taxonomy.md`); a new
`queries/athena/ctap-smvod-debug-events-raw.sql` and its row in `queries/athena/index.md` (check the index first, per `docs/guides/query-catalog.md`); a formal runner
`investigations/conviva-metrics/scripts/run_athena_debug_events_raw.py` modelled on `run_athena_debug_sessions.py` (not a scratch script: this export runs every day, so it is a tested CLI from the
start); `day_bounds()` moved from `run_athena_debug_sessions.py` into a shared helper under `src/lib/` (it is common code) and imported by both; the existing
`investigations/ctap-smvod/scripts/flatten_debug_events.py` and `scripts/lib/debug_event_parser.py` reused and, where they miss `PLAYER_EOF`, `PLAYER_BUFFER_LEVEL` or `contentmetadata` (content ID,
`contenttype`), extended (move the parser to `src/lib/` if the new folder has to import it, rather than importing across investigations); the new folder's `docs/usage.md`; the scripts registry; and
the saved export `investigations/conviva-metrics/data/athena/<TENANT>/<date>_debug_events_raw.csv` (gitignored). The POC and later tasks read this path; copy or re-fetch the ZA export once.

**What to implement:**

1. Resolve the tenant (`python scripts/resolve_tenant.py --system athena --tenant ZA`) and use its debug-events table; parameters are `database`, `debug_events_table`, `datetime_start`,
   `datetime_end`. Tenant and date are arguments (`--tenant`, `--date`, plus `--dry-run` and `--force` as in the existing runners).
2. Select `datetime`, `messageid`, `clibversion`, `clientid`, `eventclass`, `eventid` and the raw `eventdata` JSON string, unmodified (the columns `flatten_debug_events.py` expects), for every session
   event of the UTC day, ordered by `datetime`, with no sessionid filter and no event-id filter. Keep the event ids documented from `2026-10-24_debug_eventid_inventory.csv`.
3. Keep the flat parse step separate from the download (reuse `flatten_debug_events.py`), so the raw file stays the source of truth.
4. Rebuild the POC from the raw export and confirm it still gives 16 at 07:53 UTC for ZA, 2026-10-24. Record the row count and the Athena bytes scanned in the commit body or the story notes.

**Tests (no network, no real external services):**
- `test_day_bounds_happy_path` — a date gives the UTC day start and next-day start.
- `test_day_bounds_invalid_date` — a malformed date raises a clear error.
- `test_output_path` — the saved file is `<date>_debug_events_raw.csv` under the tenant folder.
- `test_flatten_player_eof_and_content` — if the parser is extended, a `PLAYER_EOF` row and a CREATE row with `contentmetadata` flatten to the expected columns.

**Commit:** `feat(conviva-metrics): cmr-cp-2`

---

## CMR-CP-3 — Explain the differences

**Files:** a new `scratch/<date>_conviva-concurrent-plays_gap_probe.py` (registry stub per `scratch/SCRATCH.md`) and a findings note in the report.

**What to implement:**

1. The 142 played sessions whose playing interval is still open at the last event: list their last events and check whether later events exist on the next UTC day.
2. The sessions in the full-day export that are not in `session.csv` or `debug_states.csv` (3,961 against 3,901 and 3,797): what they are, and whether any were playing at the peak minute.
3. Playing (16) against whole-session alive (24 at 17:36): which sessions account for the gap (buffering, pause, failed attempts).
4. State, per category, whether it belongs in Concurrent Plays under the Conviva definition.

**Commit:** `docs(conviva-metrics): cmr-cp-3`

---

## CMR-CP-4 — Prove the POC generalises

**Files:** the POC script, and a short note on any per-tenant state-name or column differences.

**What to implement:** run for one more tenant with Athena debug events (GH or ZM; check what exists locally first, otherwise fetch with the CMR-CP-2 query) and one more date, with only arguments
changed. Fix any hardcoded assumption (state names, `abr-vod-` prefix, table suffix) and record per-tenant mappings as parameters, never inline.

**Commit:** `docs(conviva-metrics): cmr-cp-4`

---

## CMR-CP-5 — Close the data gaps

**Files:** a scratch probe and findings note; the POC script and report; later an Athena query in the catalog.

**What to implement:** the device table already exists in the report (user agent from the setup span and DRM device type, covering only sessions in those exports). Remaining: the application version
(not in any local ZA export for the day; `clibversion` exists only for error sessions) and a verified playback-type source (raw `contenttype` in `eventdata`, checked on linear sessions; local ZA data
is VOD-only). Ask the user which field or service carries them; fetch only what is missing and save it for reuse. If a source does not exist, record a blocker.

**Commit:** `docs(conviva-metrics): cmr-cp-5`

---

## CMR-CP-6 — Formal recreation: graduate code and data (needs its own go-ahead)

**Files:** a Concurrent Plays script and report writer with tests in `investigations/conviva-metrics/scripts/`; pure logic (interval building, per-minute counting, interval maximum) in a testable
module there; Athena catalog entries and saved exports for every input; `src/lib/charts/` line renderer with tests, plus the shared breakdown/top-content helper and `src/lib/report_render/` writer
(this story builds them first; the attempts graduation, CMR-ATT-7, reuses them, so do not build them twice); `SCRIPTS.md`; retire the scratch copies per `scratch/SCRATCH.md`.

**Design map (from `docs/refactor/design-principles.md`, `python-hygiene-and-automation.md` and `docs/guides/functional-code-taxonomy.md`):** investigation-specific rules stay in
`investigations/conviva-metrics/`, mechanisms used by more than one metric go to `src/lib/`. Each piece is a pure function; `main()` only parses arguments and wires.

| POC piece | Formal home | Change |
|---|---|---|
| `read_events` (I/O, dedupe, sort) | loader over the CP-2 raw export (parse `eventdata` with the shared `debug_event_parser`) plus a pure `build_sessions(rows)` | split I/O from logic |
| `CLOSING_STATES`, `CLOSING_EVENTS`, `"PLAYING"` | a per-tenant state-vocabulary dataclass passed in (documented mapping, CP-4) | no module constants |
| `Event`/span tuples | frozen dataclasses or `NamedTuple` | typed |
| `playing_intervals`, `ends_open`, `per_minute`, `interval_max`, `peak`, `sessions_at` | pure module in the investigation | bucket size and day length as parameters, not `1440` |
| `alive_interval`, sensitivity and reconciliation blocks in `main` | the CP-3 gap probe, not the formal script (the report omits them) | drop from `main` |
| `read_session_csv`, `top_content`, `breakdown`, `breakdown_table` | shared helper in `src/lib/`, used by the attempts report | shared |
| `render_report` | `src/lib/report_render/` writer behind a `Protocol` | shared |
| `render_line` | `src/lib/charts/` line renderer raising `ChartError` | shared |
| `assert top == max(series)`, `SystemExit` strings, `print` | a domain error, `setup_logging()` | hygiene |
| `DATA` path and the mdrmfe glob | `src/lib/paths` and tenant config | no hardcoded paths |

**What to implement:** only after CMR-CP-1 to CMR-CP-5 are done and the user agrees. Tenant, date, interval, end rule and state mapping are arguments.

**Tests (no network, no real external services):**
- `test_playing_intervals_happy_path` — `PLAYING`, `BUFFERING`, `PLAYING`, `DESTROY` gives two intervals.
- `test_playing_intervals_open_end` — a session ending in `PLAYING` ends at its last event, and at the last event plus the timeout when one is given.
- `test_per_minute_overlap` — a session counts once in each minute its playing time overlaps, and a paused session is not counted.
- `test_failed_attempt_excluded` — a session that never reaches `PLAYING` is not counted.
- `test_equal_timestamp_order` — shuffled rows with equal timestamps give the same peak.
- `test_interval_max_equals_summary` — the summary equals the maximum of the series points.
- `test_no_playing_sessions_error` — no playing sessions on the date raises a clear error.
- `test_report_content_reconciles` — the content table plus the unresolved row equals the sessions that played during the day.

**Commit:** `feat(conviva-metrics): graduate concurrent plays poc`
