-- Purpose: usage tracking: every unified_sessions row (content name, endreason, PLAY start/end) for one household and a set of its device ids over an inclusive date range.
-- Tables: `{{database}}.unified_sessions`
-- Params: `database`, `date_end`, `date_start`, `device_ids_block`, `user_id`
-- Status: draft
-- Source:
--   - usage tracking pipeline: src/pipelines/usage_tracking/athena_source.py (user_id is the householdId; device_ids_block is a quoted, comma-separated device id list; scoped by household and device together)

SELECT
  parent_session_id,
  user_id,
  device_id,
  event_type,
  event_start,
  event_end,
  content,
  content_id,
  content_desc,
  endreason,
  timestamp_formatted
FROM "{{database}}"."unified_sessions"
WHERE timestamp_formatted BETWEEN '{{date_start}}' AND '{{date_end}}'
  AND user_id = '{{user_id}}'
  AND device_id IN ({{device_ids_block}})
ORDER BY event_start;
