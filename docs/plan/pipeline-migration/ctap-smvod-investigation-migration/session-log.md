# Session log

- 2026-10-03 — CSM-1: audited `/Users/abhadra/github_copilot/ctap-smvod-session-report/scripts/`, recorded per-file lib-vs-script decisions in `audit.md`, and confirmed the 45-file `queries/` handoff
  to CSM-6.

- 2026-10-03 — CSM-2: created the `investigations/ctap-smvod/` Rule B skeleton, ported the business-logic scripts, and rewired shared auth/Athena/CSV concerns onto `src/lib/*`.

- 2026-10-03 — CSM-3: moved the manual Step 1 expectation to `investigations/ctap-smvod/data/lightstep/`, added the operator README, and covered the ISO-prefixed path checks with tests.

- 2026-10-03 — CSM-4: moved Athena enrichment pulls to `investigations/ctap-smvod/data/athena/`, updated the pipeline/report consumers to the ISO-prefixed names, and added pull-path adapter tests.

- 2026-10-03 — CSM-5: switched investigation `output/` producers/consumers onto PT-7 snapshot/range/rollup filenames via the shared path resolver helpers and added output-path regression tests.

- 2026-10-03 — CSM-6: moved CTAP/SM-VOD Athena query text into the root query catalog, rewired the Athena/debug scripts to render catalog templates, and added a no-inline-SQL regression test.

- 2026-10-03 — CSM-7: added no-network happy-path/edge-case tests across the remaining CTAP/SM-VOD business-logic scripts, fixed the CSV-compat layer issues those tests exposed, added `RETENTION.md`,
  and pointed `CONTEXT.md` at this story folder.

- 2026-10-04 — Coordination only: this consumer does not yet call `src/lib/logging/bootstrap.py`'s `init_logging()`; see `docs/plan/logging-framework/` for the deferred bootstrap rollout rather than
  retrofitting `investigations/ctap-smvod/` in this story.
