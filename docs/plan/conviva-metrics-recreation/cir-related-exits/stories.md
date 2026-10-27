# CIR Related Exits — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: scratch work is exempt from the test gate until graduation (CMR-CIR-5); verify by running on the saved data and recording the output. Confirm scope and plan with the user before creating or
editing anything (project Steps 2-3).

**Build rule (user, 2026-10-27):** the scratch POC only validates that the metric is possible. Every formal script and helper is built while working the tasks, as tested code, not left for the end and
not run through MCP. Code specific to this story lives in `investigations/conviva-metrics/`, common code in `src/lib/`. Before writing anything new, read the existing runners and helpers and reuse or
enhance them: the raw export, session loader, `day_bounds()`, line renderer, breakdown helper and report writer all come from `../concurrent-plays/` (CMR-CP-2, CMR-CP-6). Do not copy them.

**Settled on 2026-10-27 (with the user, during the POC session):**

1. Source rule: Conviva page and the decoded formula images (see `prompt.md`).
2. The 5 s window and the 10 s seek grace are applied as stated; both are arguments.
3. Plays that end with `PLAYER_ERROR` count as ended plays.
4. The startup `BUFFERING` before the first `PLAYING` is not a stall.
5. UTC day, bucketed by session end; no Conviva reference figure exists, so no match is claimed.
6. Report: short (definition, headline with chart, top 10 content, device breakdown, playback type, each with an Unresolved row); accepted on the ZA 2026-10-24 output.

---

## CMR-CIR-1 — Settle the open definition points and the report content

**Files:** this story's `prompt.md` (definition section), the existing report `2026-10-24_ZA_cir-related-exits-report.md` if its sections change, and the `../discussion-prompt.md` Discussion log.

**What to settle with the user (discussion, no code):**

1. Whether `PAUSED` closes a stall (the POC says yes) or only `PLAYING`; what to do with repeated `BUFFERING` rows (the POC treats a run as one stall).
2. The seek reference point: `PLAYER_SEEK` has only a start time, so the 10 s grace runs from it. Check how often `PLAYER_SEEK` arrives just after the `BUFFERING` it caused (the POC would count that
   stall as CIR).
3. Sessions with `PLAYING` but no terminal event (181 on the ZA day): excluded from ended plays, or ended at their last event or on the next UTC day.
4. Scope of the impact period: whether to add session CIR time and the Conviva distribution (preset CIR-time buckets) to the report, and the 90 s expiry and under-30 s rules.
5. Chart interval: the 5-minute series is noisy (about 5 plays per bucket). Choose a coarser default (15 or 60 minutes) or a rolling view, and decide how the daily summary is stated.
6. A Conviva CIR Related Exits figure for ZA on 2026-10-24 to compare against, the tolerance that counts as a match, and the Conviva reporting timezone.

**Commit:** `docs(conviva-metrics): cmr-cir-1`

---

## CMR-CIR-2 — Explain the number

**Files:** a new `scratch/<date>_conviva-cir-related-exits_gap_probe.py` (registry stub per `scratch/SCRATCH.md`) and a findings note in the report or `prompt.md`.

**What to implement:**

1. Split the 258 exits: stall still open at the session end (BUFFERING then `DESTROY` or `PLAYER_ERROR`) against a stall that recovered within 5 s of the end. Report both counts.
2. Count the exits that sit within 10 s of a `PLAYER_SEEK` under a different grace (5, 10, 15 s) to show the sensitivity of the rule, and list sample sessions for each category.
3. The 181 plays with no end event: their last events, and whether later events exist on the next UTC day.
4. State, per category, whether it belongs in the Conviva definition.

**Commit:** `docs(conviva-metrics): cmr-cir-2`

---

## CMR-CIR-3 — Prove the POC generalises

**Files:** the POC script, and a short note on any per-tenant state-name or column differences.

**What to implement:** run for one more tenant with Athena debug events (GH or ZM; check what exists locally first, otherwise fetch with the CMR-CP-2 runner) and one more date, with only arguments
changed. Fix any hardcoded assumption (state names, the `abr-vod-` prefix, terminal events) and record per-tenant mappings as parameters, never inline.

**Commit:** `docs(conviva-metrics): cmr-cir-3`

---

## CMR-CIR-4 — Close the data gaps

**Files:** a scratch probe and findings note; the POC script and report; later an Athena query in the catalog.

**What to implement:**

1. A backgrounding signal: Conviva may count it as a session end. Check the debug events (for example `APP_KEEPALIVE` gaps, `PAUSED` then silence) and ask the user what the app emits.
2. Device and playback type: reuse the CMR-CP-5 sources (parsed user agent, DRM device type, raw `contenttype`) instead of finding them again; record any gap as a blocker.
3. Fetch only what is missing, with a catalogued query, and save it for reuse.

**Commit:** `docs(conviva-metrics): cmr-cir-4`

---

## CMR-CIR-5 — Formal recreation: graduate code and data (needs its own go-ahead)

**Files:** a CIR Related Exits script, a pure module and a report writer with tests in `investigations/conviva-metrics/scripts/`; Athena catalog entries only for inputs CMR-CIR-4 added; `SCRIPTS.md`;
retire the scratch copies per `scratch/SCRATCH.md`. The line renderer, loader, breakdown helper and report writer are the shared ones from CMR-CP-6.

**Design map (from `docs/refactor/design-principles.md`, `code-deduplication-and-taxonomy.md`, `python-hygiene-and-automation.md` and `docs/guides/functional-code-taxonomy.md`):** metric rules stay in
`investigations/conviva-metrics/`, mechanisms used by more than one metric go to `src/lib/`. Each piece is a pure function; `main()` only parses arguments and wires.

| POC piece | Formal home | Change |
|---|---|---|
| `cp.read_events` (imported from the concurrent plays POC) | the CMR-CP-6 loader over the raw export plus `build_sessions(rows)` | reuse; do not copy |
| `TERMINAL_STATES`, `"PLAYING"`, `"BUFFERING"`, `"PAUSED"`, `PLAYER_ERROR` | the per-tenant state-vocabulary dataclass from CMR-CP-6 (terminal events added) | no module constants |
| `window_s`, `grace_s` loose arguments | a frozen `CirRules` dataclass (window, grace, interval) passed in | typed, one parameter object |
| `analyse_session` (ended play, stalls, seek test, flag) | pure `ended_play`, `find_stalls`, `is_seek_induced`, `is_cir_exit`; stalls in a shareable module | SRP, likely reuse |
| `bucket_rates` with `1440 // size` | takes the day length and interval as parameters | no magic numbers |
| `top_content`, `breakdown`, `breakdown_table` (imported) | the shared helper from CMR-CP-6 | shared |
| `render_report` | the `src/lib/report_render/` writer behind a `Protocol` | shared |
| `render_line` | the `src/lib/charts/` line renderer (a percentage axis option is added there, with tests, if it is missing) | shared |
| `SystemExit` strings, `print`, the reconciliation check | domain errors and `setup_logging()`; the reconciliation becomes a tested invariant | hygiene |
| `cp.DATA` path and the mdrmfe glob | `src/lib/paths` and tenant config | no hardcoded paths |

Extensibility: a different exit window or a different seek rule is a different `CirRules` value or a function passed in (Strategy as a `Callable`), not a new branch in the flag function (OCP).

**What to implement:** only after CMR-CIR-1 to CMR-CIR-4 are done, CMR-CP-6 is done and the user agrees. Tenant, date, interval, window, grace and state mapping are arguments; the script runs on
demand and in a daily run reading the saved exports.

**Tests (no network, no real external services):**
- `test_stall_in_last_window_flags_exit` — a stall ending 3 s before a `DESTROY` gives a CIR related exit.
- `test_stall_before_window_not_flagged` — a stall that ended 6 s before the end does not.
- `test_open_stall_at_end_flagged` — `BUFFERING` then `DESTROY` counts as CIR within the window.
- `test_stall_after_seek_not_cir` — a stall starting 2 s after a `PLAYER_SEEK` is not CIR; one starting 10 s after it is.
- `test_startup_buffering_not_stall` — `BUFFERING` before the first `PLAYING` is ignored.
- `test_never_played_excluded` — a session with no `PLAYING` is not an ended play.
- `test_no_end_event_excluded` — a played session with no terminal event is not an ended play.
- `test_error_end_counts` — a `PLAYER_ERROR` after play is an ended play and can be flagged.
- `test_paused_closes_stall` — `BUFFERING`, `PAUSED`, then `DESTROY` is not an open stall.
- `test_equal_timestamp_order` — shuffled rows with equal timestamps give the same flag.
- `test_window_and_grace_are_parameters` — changing `CirRules` changes the result as expected.
- `test_series_reconciles_with_summary` — the summed series counts equal the summary counts, and the rate equals flagged over ended.
- `test_no_ended_plays_error` — no ended plays on the date raises a clear error.
- `test_report_content_reconciles` — the content table plus the unresolved row equals the flagged exits.

**Commit:** `feat(conviva-metrics): graduate cir related exits poc`
