-- Purpose: CTAP/SM-VOD every unified_sessions row (title, content id, endreason, PLAY start/end) for one household (user_id) over an inclusive date range, for the session trace.
-- Tables: `{{database}}.unified_sessions`
-- Params: `database`, `date_end`, `date_start`, `user_id`
-- Status: draft
-- Source:
--   - ctap-smvod investigation: investigations/ctap-smvod/scripts/trace_household_sessions.py (user_id is the householdId; timestamp_formatted is the YYYY-MM-DD partition)

SELECT
  parent_session_id,
  device_id,
  event_type,
  event_start,
  event_end,
  content_type,
  content,
  content_id,
  content_desc,
  endreason,
  timestamp_formatted
FROM "{{database}}"."unified_sessions"
WHERE timestamp_formatted BETWEEN '{{date_start}}' AND '{{date_end}}'
  AND user_id = '{{user_id}}'
ORDER BY event_start;
