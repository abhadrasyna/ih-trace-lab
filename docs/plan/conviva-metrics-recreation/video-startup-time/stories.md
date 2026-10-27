# Video Startup Time — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: scratch work is exempt from the test gate until graduation (CMR-VST-5); verify by running on the saved data and recording the output. Confirm scope and plan with the user before creating or
editing anything (project Steps 2-3).

**Build rule (user, 2026-10-27):** the scratch POC only validates that the metric is possible. Every formal script and helper is built while working the tasks, as tested code, not left for the end and
not run through MCP. Code specific to this story lives in `investigations/conviva-metrics/`, common code in `src/lib/`. Before writing anything new, read the existing runners and helpers and reuse or
enhance them: the raw export, session loader, `day_bounds()`, line renderer, breakdown helper and report writer all come from `../concurrent-plays/` (CMR-CP-2, CMR-CP-6). Do not copy them.

**Settled on 2026-10-27 (with the user, during the POC session and the story-creation session):**

1. Source rule: Conviva page and the decoded formula images (see `prompt.md`).
2. Attempt = `CREATE`, play start = first `PLAYING`; only sessions with both are plays.
3. Plays are bucketed by attempt time; UTC day; 5-minute interval, an argument.
4. Day summary = average over all plays, not an average of bucket averages; empty buckets are gaps in the chart.
5. Cap each play at 600 s, an argument; a negative VST is dropped and counted.
6. No Conviva reference figure exists, so no match is claimed.
7. Report accepted on the ZA 2026-10-24 output: definition, headline with chart, distribution, top 10 content, top 10 households by mean (at least 3 plays) and by worst single play (columns: plays,
   mean, median, p90, max, share over a threshold, top device), device breakdown, playback type; each table has an Unresolved row. Household tables stay in the formal report.
8. Story shape: five tasks as in `../cir-related-exits/`; High Startup Time is a follow-up story, not part of this one.

---

## CMR-VST-1 — Settle the open definition points and the report content

**Files:** this story's `prompt.md` (definition section), the existing report `2026-10-24_ZA_video-startup-time-report.md` if its sections change, and the `../discussion-prompt.md` Discussion log.

**What to settle with the user (discussion, no code):**

1. Sessions with a `PLAYING` but no `CREATE` in the day's export (a session created the previous UTC day): drop them as the POC does, or look back one day for the `CREATE`.
2. Retried or restarted starts: whether a second `CREATE` or a second `PLAYING` after a stall or an error within one session id starts a new play (the POC uses the first of each).
3. Whether `PLAYING` is the right first-frame signal or `REQUEST_VIEWING` (reconciled in CMR-VST-2).
4. Chart: the 5-minute series is noisy in thin hours; confirm 5 minutes, or add a longer default, and how the daily summary is stated beside the chart.
5. Distribution: use Conviva's ranges once CMR-VST-4 finds them; until then the POC's ranges are labelled as ours.
6. The household tables: the share-of-slow-plays threshold (10 s in the POC), the minimum plays for the mean ranking (3), and whether the full household id stays in the report.
7. A Conviva VST figure for ZA on 2026-10-24 to compare against, the tolerance that counts as a match, and the Conviva reporting timezone.

**Commit:** `docs(conviva-metrics): cmr-vst-1`

---

## CMR-VST-2 — Explain the number

**Files:** a new `scratch/<date>_conviva-video-startup-time_gap_probe.py` (registry stub per `scratch/SCRATCH.md`) and a findings note in the report or `prompt.md`.

**What to implement:**

1. The two spikes (about 72 s at 07:20 UTC, about 78 s at 20:50 UTC): list the plays in those buckets with their VST, household and device. Say whether one slow play, a few, or an outage explains
   each.
2. The 600 s play: its events, and whether the startup was real or a missed `PLAYING`.
3. The 5 plays with no `startup_time_ms` in `session.csv`, and any `PLAYING` session without a `CREATE`: why, and which side is right.
4. Reconcile `startup_time_ms` (`REQUEST_VIEWING`) with the debug-event delta on plays (zero difference on 1,505) and show what `startup_time_ms` measures on sessions that never played, so nobody uses
   the column alone as VST.
5. State, per category, whether it belongs in the Conviva definition.

**Commit:** `docs(conviva-metrics): cmr-vst-2`

---

## CMR-VST-3 — Prove the POC generalises

**Files:** the POC script, and a short note on any per-tenant state-name or column differences.

**What to implement:** run for one more tenant with Athena debug events (GH or ZM; check what exists locally first, otherwise fetch with the CMR-CP-2 runner) and one more date, with only arguments
changed. Fix any hardcoded assumption (the `CREATE` and `PLAYING` names, the `abr-vod-` prefix, the `setupsession_with_outcome.csv` and mDRM paths, the household column) and record per-tenant mappings
as parameters, never inline.

**Commit:** `docs(conviva-metrics): cmr-vst-3`

---

## CMR-VST-4 — Close the data gaps

**Files:** a scratch probe and findings note; the POC script and report; later an Athena query in the catalog.

**What to implement:**

1. Conviva's distribution ranges: ask the user for the Conviva page or export that lists the preset VST buckets (the metric page does not); replace the POC ranges.
2. Heartbeat gap and loss during startup: check whether any debug event (`APP_KEEPALIVE` or equivalent) can stand in; ask the user what the app emits. Record the exclusion as not modelled if none.
3. Pre-roll ads: confirm with the user that CTAP VOD has no client-side pre-roll; if it has, find the ad start and end events and subtract them as in the Conviva formula.
4. Device and playback type: reuse the CMR-CP-5 sources (parsed user agent, DRM device type, raw `contenttype`) instead of finding them again; record any gap as a blocker.
5. Fetch only what is missing, with a catalogued query, and save it for reuse.

**Commit:** `docs(conviva-metrics): cmr-vst-4`

---

## CMR-VST-5 — Formal recreation: graduate code and data (needs its own go-ahead)

**Files:** a VST script, a pure module and a report writer with tests in `investigations/conviva-metrics/scripts/`; Athena catalog entries only for inputs CMR-VST-4 added; `SCRIPTS.md`; retire the
scratch copies per `scratch/SCRATCH.md`. The line renderer, loader, breakdown helper and report writer are the shared ones from CMR-CP-6.

**Design map (from `docs/refactor/design-principles.md`, `code-deduplication-and-taxonomy.md`, `python-hygiene-and-automation.md` and `docs/guides/functional-code-taxonomy.md`):** metric rules stay in
`investigations/conviva-metrics/`, mechanisms used by more than one metric go to `src/lib/`. Each piece is a pure function; `main()` only parses arguments and wires.

| POC piece | Formal home | Change |
|---|---|---|
| `cp.read_events` (imported from the concurrent plays POC) | the CMR-CP-6 loader over the raw export plus `build_sessions(rows)` | reuse; do not copy |
| `"PLAYER_SESSION_EVENT"`, `"CREATE"`, `"PLAYER_STATE_CHANGE"`, `"PLAYING"` literals | the per-tenant state-vocabulary dataclass from CMR-CP-6 | no module constants |
| `cap_seconds`, `interval`, `slow_seconds`, `min_plays` loose arguments | a frozen `VstRules` dataclass passed in | typed, one parameter object |
| `startup` (attempt time, seconds to first frame) | pure `find_play(events, vocab)` returning a typed `Play`, plus `cap(play, rules)` | SRP, reuse by High Startup Time |
| `bucket_average`, `counts_per_bucket` with `1440 // size` | take the day length and interval as parameters; one function returns sum and count per bucket | no magic numbers |
| `distribution` with the module `BINS` | ranges come from `VstRules` (Conviva's, once CMR-VST-4 finds them) | data, not code |
| `household_table`, `group_table` | pure `rank_households(plays, rank_by, min_plays)` returning rows, plus the shared breakdown helper (CMR-CP-6) | logic apart from rendering |
| the `math.ceil` nearest-rank percentile and `statistics.median` | one tested `percentile()` helper in `src/lib/` (shared with CIR and attempts if they need it) | shared |
| `render_report` | the `src/lib/report_render/` writer behind a `Protocol` | shared |
| `render_line` | the `src/lib/charts/` line renderer (an optional seconds axis unit is added there, with tests, if missing; gaps for empty buckets) | shared |
| `SystemExit`, `print`, reconciliation check, stdout comparison | domain errors, `setup_logging()`; reconciliation a tested invariant; comparison a flag or dropped | hygiene |
| `cp.DATA` path and the mdrmfe glob | `src/lib/paths` and tenant config | no hardcoded paths |

Extensibility: a different cap, interval or distribution is a different `VstRules` value, and a different first-frame signal is a function passed in (Strategy as a `Callable`), not a new branch (OCP).
High Startup Time reuses `find_play` and `cap`, so the pure module must not import the report or chart code (DIP).

**What to implement:** only after CMR-VST-1 to CMR-VST-4 are done, CMR-CP-6 is done and the user agrees. Tenant, date, interval, cap, thresholds and state mapping are arguments; the script runs on
demand and in a daily run reading the saved exports.

**Tests (no network, no real external services):**
- `test_vst_is_first_playing_minus_create` — `CREATE` at 10:00:00 and `PLAYING` at 10:00:06 give 6 s.
- `test_first_playing_wins_after_rebuffer` — a later `PLAYING` after `BUFFERING` does not change the VST.
- `test_never_played_excluded` — a session with no `PLAYING` is not a play.
- `test_play_without_create_excluded` — `PLAYING` with no `CREATE` is not a play and is counted separately.
- `test_cap_applied` — 900 s becomes 600 s; the cap is a parameter and a different cap changes the result.
- `test_negative_vst_dropped_and_counted` — `PLAYING` before `CREATE` is dropped and reported.
- `test_bucketed_by_attempt_time` — a play that starts in one bucket and begins playing in the next is counted in the attempt's bucket.
- `test_equal_timestamp_order` — shuffled rows with equal timestamps give the same VST.
- `test_summary_is_average_over_plays` — the day value equals the mean of all plays, not the mean of bucket averages.
- `test_empty_bucket_is_gap` — a bucket with no plays has no value, not zero.
- `test_series_reconciles_with_summary` — the bucket counts add up to the number of plays, and plays plus never-played plus other-day plus unusable equal the sessions.
- `test_distribution_counts_add_up` — the range counts add up to the plays and respect the range edges.
- `test_household_ranking_min_plays` — a one-play household does not enter the mean ranking but does enter the worst-single-play ranking.
- `test_household_percentile_small_group` — nearest-rank p90 is never below the median for groups of one or two plays.
- `test_no_plays_error` — no plays on the date raises a clear error.
- `test_report_content_reconciles` — each breakdown table plus its Unresolved row equals the number of plays.

**Commit:** `feat(conviva-metrics): graduate video startup time poc`
