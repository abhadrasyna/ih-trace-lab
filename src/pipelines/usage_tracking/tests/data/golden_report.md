# Household usage report - ZA - 2026-11-02

**Summary:** 1 HHIDs, 2 devices, 1 active, 2 sessions, 1 errors.

## Team A (22ZVg5…)

| Person | Device | Active | Sessions | Watch min | Errors | Top content | Lightstep reqs | Flags |
|---|---|---|---|---|---|---|---|---|
| Sai | 1f1a0cca | yes | 2 | 29.4 | 1 | Family Feud South Africa | 9 | error_endreason |
| Fayaz | 2b27dfd7 | no | 0 | 0.0 | 0 | - | 0 | - |

### Sai - sessions

| Time | parent_session_id | Content | Endreason | Error | trace_id |
|---|---|---|---|---|---|
| 19:19:06 | abr-vod-1 | Family Feud South Africa | DESTROY | - | trace-aaa |
| 20:00:00 | abr-vod-2 | True to the Game | PLAYER_ERROR | 6007 Test device \| not allowed | trace-bbb (+1) |

## Anomalies

- Team A `22ZVg5IOnUplWxLRa_VVWbs4mE7H41Pp4pInR4UZtqnoiPgBjIcz`: **error_endreason** device `1f1a0cca3e643b1d9058` - abr-vod-2 ended PLAYER_ERROR (code 6007)
- Team A `22ZVg5IOnUplWxLRa_VVWbs4mE7H41Pp4pInR4UZtqnoiPgBjIcz`: **new_device** device `9999aaaabbbbccccdddd` - not in roster; first seen 2026-11-02 21:00:00, 2 sessions

## 7-day trend (sessions per day)

| Household | Person | 10-27 | 10-28 | 10-29 | 10-30 | 10-31 | 11-01 | 11-02 |
|---|---|---|---|---|---|---|---|---|
| Team A | Sai | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| Team A | Fayaz | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
