# Tenant playback status summary — 2026-10-08 (SA, GH, ZM)

One-day status across three tenants, built from `output/<TENANT>/2026-10-08_setupsession_with_outcome.csv` (rows deduplicated by `sessionId`; a session can span several ctap traces). Day is UTC.

## Headline

The headline measure is **played OK**: the session's `state_sequence` reached `PLAYING` and the session carries no error code. It is a proxy computed from the player state sequence, not an official
success rate.

| 08 Oct (UTC) | SA | GH | ZM |
|---|---|---|---|
| Playback sessions | 2,050 | 908 | 185 |
| Devices / households | 458 / 450 | 41 / 31 | 49 / 47 |
| **Played OK (reached PLAYING, no error)** | **836 (41%)** | **732 (81%)** | **77 (42%)** |
| Failed with an error code | 733 (36%) | 110 (12%) | 64 (35%) |
| Neither played nor errored (stalled, timed out, no data) | 481 (23%) | 66 (7%) | 44 (24%) |
| Error sessions that never reached PLAYING | 669 of 733 (91%) | 104 of 110 (95%) | 31 of 64 (48%) |
| Error concentration (top 4 devices' share of error sessions) | 12% | 58% | 58% |
| Playback position never advanced | 39% | 22% | 28% |
| Startup time, median / p75 | 4.0 s / 7.6 s | 3.8 s / 9.6 s | 9.7 s / 21.0 s |
| Main device class | Mobile 87% | Desktop 92% | Mobile 71% |

## Playback outcome (share of all sessions)

`INCOMPLETE_NO_DESTROY` is deliberately omitted: it is the ambiguous bucket (it also swallows viewing-start failures, see `knowledge/mtn-adoption-playback-outcome-classification-gap.md`). Sessions
with no Athena outcome are omitted too, so columns do not sum to 100%.

| Outcome | SA | GH | ZM |
|---|---|---|---|
| DESTROY (clean end) | 692 (34%) | 456 (50%) | 50 (27%) |
| TIMEOUT | 149 (7%) | 265 (29%) | 29 (16%) |
| EBVS | 126 (6%) | 57 (6%) | 17 (9%) |
| PLAYER_ERROR | 49 (2%) | 6 (<1%) | 29 (16%) |

## Error codes (sessions, % of the tenant's sessions)

| Code | SA | GH | ZM |
|---|---|---|---|
| 6001 | 612 (30%) | 1 (<1%) | 0 |
| 1003 | 61 (3%) | 63 (7%) | 43 (23%) |
| 3016 | 28 (1%) | 26 (3%) | 4 (2%) |
| E31012 | 17 (<1%) | 3 (<1%) | 6 (3%) |
| 6007 | 2 | 1 | 5 (3%) |
| 1001 | 2 | 0 | 4 (2%) |
| 6006 | 1 | 8 (<1%) | 0 |
| 1002 | 3 | 8 (<1%) | 1 |
| Other (6002, 1006, E1003) | 10 | 0 | 1 |
| **Sessions with any error** | **733 (36%)** | **110 (12%)** | **64 (35%)** |

Counts are sessions per code; a session can carry more than one code (3 in SA, none in GH, not checked for ZM), so rows can slightly exceed the "any error" total.

## Takeaways

1. **GH is healthy.** About 8 in 10 sessions play cleanly; errors are few and 58% sit on 4 devices, so a targeted device fix would move the number.
2. **SA is systemic.** Only ~4 in 10 sessions play cleanly and one code, 6001, is 83% of error sessions, spread across many devices (top 4 = 12%). Over 90% of SA failures happen before playback
   starts.
3. **ZM is small but poor, with a different failure shape.** Also ~4 in 10 play cleanly, but error 1003 dominates (67% of error sessions), only 48% of failures occur before playback (the rest fail
   mid-stream), PLAYER_ERROR is 16% of sessions, and startup is the slowest (median 9.7 s).
4. **1003 is the common thread** across GH and ZM (and present in SA), while 6001 is effectively SA-only.

## Caveats

- Single day; ZM has only 185 sessions, so its percentages move a lot with a few sessions. Compare against 04–07 Oct before calling a trend.
- The played-OK rate is a `state_sequence` proxy; the "neither" bucket (SA 23%, ZM 24%) is unexplained and probably mixes timeouts, stalls and sessions with no Athena data.
- Sessions with no Athena outcome: SA 359 (18%), GH 28 (3%), ZM 28 (15%).
- The `error_descriptions` field is empty for 6001 and 3016, so what these codes mean cannot be stated from this data.
- VSF (viewing start failure) is not measurable here; the pipeline's Athena export lacks `REQUEST_VIEWING`, and `state_sequence` is only a proxy for failure before playback.
- Computed with a throwaway script (no script committed); numbers are reproducible from the CSVs above with the definitions in this file.
