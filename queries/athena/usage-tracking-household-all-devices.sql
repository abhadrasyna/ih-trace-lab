-- Purpose: usage tracking: every distinct device_id seen on one household for one day with its session count and first event time, with no device filter, to flag devices missing from the roster.
-- Tables: `{{database}}.unified_sessions`
-- Params: `database`, `date`, `user_id`
-- Status: draft
-- Source:
--   - usage tracking pipeline: src/pipelines/usage_tracking/athena_source.py (user_id is the householdId; timestamp_formatted is the YYYY-MM-DD partition)

SELECT
  device_id,
  COUNT(DISTINCT parent_session_id) AS session_count,
  MIN(event_start) AS first_seen
FROM "{{database}}"."unified_sessions"
WHERE timestamp_formatted = '{{date}}'
  AND user_id = '{{user_id}}'
GROUP BY device_id
ORDER BY first_seen;
