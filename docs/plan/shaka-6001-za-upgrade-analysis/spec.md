# Shaka 6001 ZA upgrade analysis — spec (audit and reuse)

> Evidence for what already exists, so each task reuses or promotes instead of rewriting (`docs/refactor/code-deduplication-and-taxonomy.md`). No task checkboxes here.

## Reuse table

| Need | Existing code | Decision |
|---|---|---|
| User-agent parsing (model, build, Android, Chrome, `wv`) | `ctap-smvod/scripts/parse_debug_user_agents.py::parse_user_agent` | Promote to `src/lib/user_agent/`; `ctap-smvod` re-exports. |
| Webview and success checks | `ctap-smvod/scripts/analyze_webview_devices.py` (`_is_wv`, `_is_success`; private) | Promote public `is_webview`, `is_success` (`DESTROY`) to `src/lib/`. |
| Eventdata flattening | `ctap-smvod/scripts/lib/debug_event_parser.py` | Promote the used functions with SU-4; no cross-investigation import. |
| Ranking by error | `ctap-smvod/scripts/rank_households_by_error.py::rank_households` | Generalise into a shared `src/lib/ranking/` helper used by SU-12 and SU-13. |
| Athena client | `src/lib/athena` (`AthenaClient` Protocol, `AthenaAdapter`) | Inject; never build a client in a script. |
| Paths | `config/data_paths.yaml`, `src/lib/paths` (`YamlPathResolver`) | Use for data and output dirs: `investigations/shaka-6001/{data,output}/<tool>/<TENANT>`. |
| CSV | `src/lib/csv_io` | Use for reads and writes. |
| Charts | `src/lib/charts` (`render_*`, `write_chart_png`, `ChartError`) | Use as-is. |
| Playback outcome query | `queries/athena/ctap-smvod-playback-outcome.sql` | Reuse; fetch only dates missing locally. |
| Navigation counts query | `queries/athena/fact-navigation-interactions-event-source-timestamp-formatted.sql` | Extend for the redirect extract (SU-8). |
| Local ZA 6001 data | `investigations/shaka-6001/data/athena/ZA/*_error_eventdata_codes-6001.csv` (2026-10-01 to 2026-11-06) | First data source for SU-4 onward. |

## Facts established on 2026-11-06 (Athena, ZA)

- `guestLoginPrompt-redirect` rows in `fact_navigation_interactions`: 1 on 2026-11-02, 280 on 2026-11-04 (148 users), 608 on 2026-11-05 (315 users). All `user_id` values are `GUEST.<uuid>`.
- `nav_event_time` is UTC; `timestamp_formatted` is only a date.
- All 462 redirect guests on 2026-11-04 and 2026-11-05 have events in `e6auj7k7_ccl_debug_events`, where `clientid` is `<uuid>:GUEST.<uuid>`. One debug day scans about 650 MB.
- The first redirect on 2026-11-04 is 11:15 UTC (16:45 IST), inside the upgrade window, and its debug events still carry `appversion v2026.10.27.01`.
- No subscription-date column was found in the known tables; tenure uses first-seen as a proxy.

## Shared-library placement

New shared logic goes in `src/lib/` per `docs/guides/functional-code-taxonomy.md`; add the new targets (`user_agent`, `playback`, `ranking`) to that guide in SU-2. Investigation-specific code (config,
period classification, loaders, analyses) stays in `investigations/shaka-6001/scripts/`.
