WITH session_outcomes AS (
    SELECT
        parent_session_id,
        {{select_identity_columns}}
        timestamp_formatted,
        COALESCE(
            MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
            CASE WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1
                 THEN 'EBVS'
                 ELSE 'INCOMPLETE_NO_DESTROY'
            END
        ) AS playback_outcome
    FROM "{{database_identifier}}"."unified_sessions"
    WHERE date(timestamp_formatted) >= date '{{start_date}}'
      AND date(timestamp_formatted) < date '{{end_date_exclusive}}'
    GROUP BY parent_session_id, {{group_identity_columns}} timestamp_formatted
)
SELECT
    {{session_date_expr}} AS session_date,
    count(distinct {{distinct_expression}}) AS metric_value
FROM session_outcomes
WHERE playback_outcome = '{{outcome_value}}'
GROUP BY 1
ORDER BY 1;
