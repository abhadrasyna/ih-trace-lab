# Tenant playback status summary — 2026-10-07 (ZA, GH, ZM)

Built by `scripts/summarize_tenant_status.py` from `output/<TENANT>/…_setupsession_with_outcome.csv`; rows without a `sessionId` (ctap-only traces) are dropped. Day is UTC. **Played OK** = the
session's `state_sequence` reached `PLAYING` and it carries no error code (a proxy, not an official success rate).

## Headline

|  | ZA | GH | ZM |
|---|---|---|---|
| Playback sessions | 2,068 | 35 | 311 |
| Devices / households | 446 / 435 | 5 / 5 | 98 / 97 |
| **Played OK** | **1,114 (54%)** | **8 (23%)** | **137 (44%)** |
| Failed with an error code | 485 (23%) | 4 (11%) | 67 (22%) |
| Neither played nor errored | 469 (23%) | 23 (66%) | 107 (34%) |
| Error sessions that never reached PLAYING | 415 of 485 (86%) | 4 of 4 (100%) | 22 of 67 (33%) |
| Top 4 devices' share of error sessions | 15% | 100% | 57% |
| Playback position never advanced | 27% | 17% | 19% |
| Startup median / p75 | 4.5 s / 7.6 s | 14.0 s / 21.2 s | 9.6 s / 16.9 s |
| Main device class | Mobile 85% | Desktop 66% | Mobile 81% |

## Playback outcome (share of all sessions)

`INCOMPLETE_NO_DESTROY` and sessions with no Athena outcome are omitted, so columns do not sum to 100%.

|  | ZA | GH | ZM |
|---|---|---|---|
| DESTROY | 936 (45%) | 7 (20%) | 104 (33%) |
| TIMEOUT | 178 (9%) | 1 (3%) | 34 (11%) |
| EBVS | 116 (6%) | 2 (6%) | 32 (10%) |
| PLAYER_ERROR | 58 (3%) | 0 (0%) | 41 (13%) |

## Error codes (sessions, % of the tenant's sessions)

|  | ZA | GH | ZM |
|---|---|---|---|
| 6001 | 352 (17%) | 0 (0%) | 1 (<1%) |
| 1003 | 54 (3%) | 3 (9%) | 45 (14%) |
| E31012 | 28 (1%) | 1 (3%) | 11 (4%) |
| 3016 | 24 (1%) | 0 (0%) | 1 (<1%) |
| 6007 | 5 (<1%) | 0 (0%) | 4 (1%) |
| 1001 | 5 (<1%) | 0 (0%) | 3 (<1%) |
| 6002 | 6 (<1%) | 0 (0%) | 0 (0%) |
| 6008 | 6 (<1%) | 0 (0%) | 0 (0%) |
| Other | 5 | 0 | 2 |
| **Sessions with any error** | **485 (23%)** | **4 (11%)** | **67 (22%)** |

A session can carry several codes, so rows can slightly exceed the "any error" total.

## Caveats

- Single day; small tenants' percentages move a lot with a few sessions.
- Sessions with no Athena outcome: ZA 367 (18%), GH 21 (60%), ZM 76 (24%).
- VSF (viewing start failure) is not measurable from this export; `state_sequence` is only a proxy for failure before playback.
- Takeaways are not generated; add them by hand.
