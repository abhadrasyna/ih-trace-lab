-- Purpose: 21e. Direct session lookups — the exact contentId-present vs contentId-missing comparison from SDI-77439
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `parent_session_id_pattern`, `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 15. Sessions stuck with endreason = 'PLAYING' and no PLAY row (11 Jul 2026)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 21e. Direct session lookups — the exact contentId-present vs contentId-missing comparison from SDI-77439
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 8. Final aggregated outcome query — one row per session, all event types, EBVS/INCOMPLETE_NO_DESTROY classification
--   - ctap-smvod-session-report/queries/athena_session_outcome.md :: Query (final — one row per session, all event types, EBVS/INCOMPLETE_NO_DESTROY classification)

SELECT * FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}} and parent_session_id like {{parent_session_id_pattern}};

SELECT * FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}} and parent_session_id like {{parent_session_id_pattern}};
