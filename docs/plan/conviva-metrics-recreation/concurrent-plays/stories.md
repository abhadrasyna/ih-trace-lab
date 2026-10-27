# Concurrent Plays — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: scratch work is exempt from the test gate until graduation (CMR-CP-6); verify by running on the saved data and recording the output. Confirm scope and plan with the user before creating or
editing anything (project Steps 2-3).

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

**Files:** a new `queries/athena/ctap-smvod-debug-events-raw.sql` and its row in `queries/athena/index.md` (check the index first, per `docs/guides/query-catalog.md`); a scratch runner
`scratch/<date>_conviva-concurrent-plays_raw_export.py` with its registry stub; the saved export `investigations/ctap-smvod/data/athena/<TENANT>/<date>_debug_events_raw.csv` (gitignored).

**What to implement:**

1. Resolve the tenant (`python scripts/resolve_tenant.py --system athena --tenant ZA`) and use its debug-events table; parameters are `database`, `debug_events_table`, `datetime_start`,
   `datetime_end`.
2. Select `datetime`, `eventid` and the raw `eventdata` JSON string, unmodified, for every session event of the UTC day, ordered by `datetime`, with no sessionid filter and no event-id filter. Keep
   the event ids documented from `2026-10-24_debug_eventid_inventory.csv`.
3. Make a second, flat parse step that is separate from the download, so the raw file stays the source of truth.
4. Rebuild the POC from the raw export and confirm it still gives 16 at 07:53 UTC for ZA, 2026-10-24. Record the row count and the Athena bytes scanned.

**Commit:** `chore(conviva-metrics): cmr-cp-2`

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

**Files:** a `scripts/dev/` Concurrent Plays script and report writer with tests; pure logic (interval building, per-minute counting, interval maximum) in a testable module; Athena catalog entries and
saved exports for every input; `src/lib/charts/` line renderer with tests (shared with the attempts graduation, CMR-ATT-7, so do not build it twice); `SCRIPTS.md`; retire the scratch copies per
`scratch/SCRATCH.md`. Shape it with `docs/refactor/` and `docs/guides/functional-code-taxonomy.md`: investigation-specific code in its script, common code in `src/lib/`.

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
