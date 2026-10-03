SELECT
  parent_session_id AS sessionId,
  MAX(user_id)   AS householdId,
  MAX(device_id) AS deviceId,
  MAX(content)   AS content,
  COALESCE(
    MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
    CASE WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1
         THEN 'EBVS'
         ELSE 'INCOMPLETE_NO_DESTROY'
    END
  ) AS playback_outcome,
  MAX(CASE WHEN event_type = 'PLAY' THEN event_start END) AS event_start,
  MAX(CASE WHEN event_type = 'PLAY' THEN event_end END)   AS event_end,
  MAX(CASE WHEN event_type = 'REQUEST_VIEWING'
           THEN date_diff('millisecond', event_start, event_end) END)
    AS startup_time_ms,
  SUM(CASE WHEN event_type = 'BUFFERING' THEN 1 ELSE 0 END)
    AS buffering_count,
  SUM(CASE WHEN event_type = 'BUFFERING'
           THEN date_diff('millisecond', event_start, event_end) ELSE 0 END)
    AS buffering_total_ms
FROM "{{database_identifier}}"."unified_sessions"
WHERE timestamp_formatted = '{{date}}'
  {{session_filter}}
GROUP BY parent_session_id;
