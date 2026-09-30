# vod-playback-timing-probe migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## VTP-1 — audit + per-file classification (audit-only, blocked on `src/lib/mpd/`)

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table. Do not begin any actual port — `src/lib/mpd/` does not exist yet.

**What to implement:**

1. Re-read all implementation files under `/Users/abhadra/github_copilot/vod-playback-timing-probe/scripts/` (top-level scripts + the `playback_probe/` package, ~35 files — see `spec.md` §1 for the
   full list).
2. Confirm or refine `spec.md` §1's classification — state the FCT-1 test result explicitly per file.
3. Explicitly list which files depend on `mpd_parser.py` (directly or transitively) and are therefore blocked until `src/lib/mpd/` exists, versus which files can be ported independently once
   `src-lib-migration`'s other five modules (`har`, `auth`, `curl_to_python`, `report_render`, `paths`) land.
4. Check `docs/plan/src-lib-migration/README.md` for whether `src/lib/mpd/` has been added to that epic's module list yet (per this epic's own coordination note); if not, state that the actual port
   cannot start until it is.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(vod-playback-timing-probe-tool-migration): audit scripts and classify lib vs. business logic`
