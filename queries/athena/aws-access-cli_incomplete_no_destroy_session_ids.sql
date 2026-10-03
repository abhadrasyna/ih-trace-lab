WITH session_outcomes AS (
    SELECT
        parent_session_id,
        timestamp_formatted,
        COALESCE(
            MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
            CASE WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1
                 THEN 'EBVS'
                 ELSE 'INCOMPLETE_NO_DESTROY'
            END
        ) AS playback_outcome,
        MAX(CASE WHEN event_type = 'REQUEST_VIEWING' AND endreason = 'PLAYER_ERROR'
                 THEN 1 ELSE 0 END) AS is_vsf
    FROM "{{database_identifier}}"."unified_sessions"
    WHERE date(timestamp_formatted) >= date '{{start_date}}'
      AND date(timestamp_formatted) < date '{{end_date_exclusive}}'
    GROUP BY parent_session_id, timestamp_formatted
)
SELECT
    date(timestamp_formatted) AS session_date,
    parent_session_id AS session_id
FROM session_outcomes
WHERE playback_outcome = 'INCOMPLETE_NO_DESTROY' AND is_vsf = 0
ORDER BY 1, 2;
