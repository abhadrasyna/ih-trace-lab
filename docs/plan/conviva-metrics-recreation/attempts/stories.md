# Attempts — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: scratch scripts are exempt from the test gate until graduation (CMR-ATT-7); verify by running on local data and recording the output. Confirm scope and plan with the user before creating or
editing anything (project Steps 2-3).

---

## CMR-ATT-1 — POC script: per-interval attempts from Athena CREATE events (done)

**Files:** `scratch/2026-10-26_conviva-attempts_timeseries_poc.py`, `SCRIPTS.md` (registry).

**Delivered:** args `--tenant`, `--date`, `--interval`, `--out-dir`; first CREATE per `sessionId`, filtered to the UTC date, bucketed, zero-filled; prints the sum of the series and the overlap with
`session.csv`, `outcome_first_debug.csv` and the Lightstep smvod export. **Commit:** `c61dafe`.

---

## CMR-ATT-2 — Chart on the shared theme (done)

**Files:** `scratch/_lib/line_chart.py` (`render_line`), the POC script.

**Delivered:** dark theme and fonts from `src/lib/charts`, single `series[0]` line with a flat 0.22-alpha fill, zero baseline, abbreviated y-axis, HH:MM x-axis, saved with `write_chart_png` under
`<out-dir>/<tenant>/charts/`. Default bucket 5 minutes. **Commit:** `eba7b97`.

---

## CMR-ATT-3 — Chart header streamlined (done)

**Files:** `scratch/_lib/line_chart.py`, the POC script.

**Delivered:** title "Attempts — <tenant>, <date>" only; a large KPI (the sum of points) directly under it; interval, UTC and base in a small muted footer. A variant with a 30-minute moving average
and a `HeaderCell` header was tried and rejected by the user (the plain line was clearer). **Commit:** `04a6f01`.

---

## CMR-ATT-8 — Supporting markdown report (done)

**Files:** the POC script (`--report-dir`, `--top`); output `attempts/<date>_<tenant>_attempts-report.md`.

**Delivered:** the report embeds the chart, states the headline (attempts, peak bucket) and a top-N content table (attempts, share of all attempts, unique households) from Athena `session.csv`, plus a
"Not resolved" row so the table reconciles to the total. For ZA, 2026-10-24: 3,901 attempts, 141 without a title. The chart link points into the gitignored `output/`. **Commit:** `01d0df6`.

---

## CMR-ATT-4 — Explain the gaps

**Files:** a new `scratch/<date>_conviva-attempts_gap_probe.py` (registry stub per `scratch/SCRATCH.md`); findings in a `scratch/<date>_conviva-attempts_gap_findings.md` note.

**What to implement:**

1. List the 138 CREATE sessions missing from `session.csv` and the 140 missing from `outcome_first_debug.csv`; classify them by events present (no state change, error only, session shorter than the
   export window, CREATE at the day edge).
2. List the 34 `session.csv` sessions with no CREATE on the date and check whether their CREATE falls on the previous UTC day.
3. For the Lightstep extras, check what they are (span or session scope, retries, other days) before calling them overcount.
4. State, per category, whether it belongs in Attempts under the Conviva definition.

**Commit:** `docs(conviva-metrics): cmr-att-4`

---

## CMR-ATT-5 — Settle the open definition points

**Files:** this story's `prompt.md` (definition section) and the `../discussion-prompt.md` Discussion log.

**What to settle with the user:** the formula image on the Conviva page; a Conviva Attempts figure for ZA on 2026-10-24 (summary and time series) to compare against; UTC versus local day boundary;
whether auto-play counts in our player; how revived sessions map to our `sessionId`s. Record each answer, or mark it an assumption.

**Commit:** `docs(conviva-metrics): cmr-att-5`

---

## CMR-ATT-6 — Prove the POC generalises

**Files:** the POC script, and a short note on any per-tenant file or column differences.

**What to implement:** run for one more tenant that has Athena `debug_states` data (GH or ZM, check what exists locally first) and one more date, with only arguments changed. Fix any hardcoded
assumption found, and record per-tenant mappings as parameters, never inline.

**Commit:** `docs(conviva-metrics): cmr-att-6`

---

## CMR-ATT-9 — Close the data gaps for the report

**Files:** a scratch probe and findings note; the POC script and report; later an Athena query in the catalog (`docs/guides/query-catalog.md`).

**What to implement:**

1. Find what marks a session as linear or VOD for ZA. Local data is VOD-only (`abr-vod-` session ids, VOD playback URLs); ask the user which service or session prefix carries linear.
2. Find a device-type or app field. `session.csv` has only a hashed `deviceId`; the ctap Lightstep export has `http.user_agent` (browser/OS only).
3. Fetch only what is missing (tenant resolved first, ZA and 2026-10-24) and save it where later sessions can reuse it.
4. Add the second chart (linear vs VOD attempts, same renderer and theme) and a top-10 device table to the report. If a source does not exist, record it as a blocker, not a guess.

**Commit:** `docs(conviva-metrics): cmr-att-9`

---

## CMR-ATT-7 — Formal recreation: graduate code and data (needs its own go-ahead)

**Files:** `scripts/dev/` attempts script and report writer with tests; Athena query catalog entries and saved exports for every input the report needs; `src/lib/charts/` line renderer with tests;
`SCRIPTS.md`; retire the scratch copies per `scratch/SCRATCH.md`.

**What to implement:** only after CMR-ATT-4 to CMR-ATT-6 and CMR-ATT-9 are done and the user agrees. The renderer gets the same signature style and `ChartError` handling as the other `src/lib/charts`
renderers, and the guide's module table gains the new module.

**Tests (no network, no real external services):**
- `test_attempts_bucketing_happy_path` — CREATE events land in the expected buckets and the sum equals the distinct session count.
- `test_attempts_missing_create_events` — no CREATE rows for the date raises a clear error.
- `test_render_line_png_magic` — output starts with `\x89PNG`.
- `test_attempts_report_top_content` — the top-N table is sorted and its rows plus the unresolved row equal the attempts total.
- `test_attempts_report_no_titles` — no resolved titles gives a table with only the unresolved row, no crash.
- `test_render_line_empty_series` — empty input raises `ChartError`.

**Commit:** `feat(conviva-metrics): graduate attempts poc`
