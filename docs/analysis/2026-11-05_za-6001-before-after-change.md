# ZA PLAYER_ERROR 6001 before and after the application change

Analysis of errorcode 6001 on the ZA tenant (`unified_e6auj7k7`) around an application upgrade intended to reduce it. All times are UTC.

## Question

Did the upgrade deployed at 2026-11-04 11:30 UTC reduce 6001 errors, and do devices that hit 6001 go on to play successfully?

## Method

- Window: 2026-11-03 23:30 UTC to 2026-11-04 23:30 UTC (24 hours), centred on the change at 2026-11-04 11:30 UTC.
- Failures: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `eventid = 'PLAYER_ERROR'`, `errorcode` read from the `eventdata` JSON. Device and household come from splitting `clientid` on `:` (64-char
  device id, 52-char household id).
- Playback outcome: `unified_e6auj7k7.unified_sessions`, `event_type = 'PLAY'` summary rows. `endreason = 'DESTROY'` is treated as a successful playback; this is an assumption from the observed values
  (`DESTROY`, `TIMEOUT`, `PLAYER_ERROR`), not a documented rule.
- Only aggregate counts were produced; no household or device ids are recorded here.

## Findings

### 6001 volume, before vs after the change

| Period (UTC) | PLAYER_ERRORs | 6001 events | 6001 sessions | Distinct devices | Distinct households | 6001 share of errors |
|---|---|---|---|---|---|---|
| 2026-11-03 23:30 to 2026-11-04 11:30 (before) | 422 | 290 | 264 | 233 | 231 | 69% |
| 2026-11-04 11:30 to 2026-11-04 23:30 (after) | 781 | 601 | 318 | 123 | 123 | 77% |

- 6001 did not drop. Events roughly doubled and the share of all player errors rose from 69% to 77%.
- Fewer households were affected (231 to 123), but each hit 6001 more often: about 1.3 events per household before and about 4.9 after. Events per session rose from 1.1 to 1.9, which points to retry
  loops.
- The windows are not like-for-like in traffic: the after window contains the evening peak. There is no session-volume denominator, so this does not show whether the change made things worse.

### Do devices recover after a 6001?

| First 6001 was | Devices with 6001 | Later successful playback | Success after the last 6001 | Later PLAYER_ERROR | Any later PLAY row |
|---|---|---|---|---|---|
| Before 2026-11-04 11:30 UTC | 233 | 5 | 2 | 1 | 6 |
| After 2026-11-04 11:30 UTC | 115 | 1 | 1 | 1 | 1 |

- Recovery is rare: 2.6% of devices before the change and 0.9% after.
- Most 6001 devices have no later `PLAY` row at all, so either they give up or the failure happens before a session is recorded.
- Devices are bucketed by their first 6001, so the 115 here differ from the 123 above, which includes devices whose first 6001 was before the change.

## Conclusion

No evidence that the change reduced 6001 in the 12 hours after it. The result is inconclusive on whether it got worse, because the traffic denominator is missing.

## Caveats

- `TIMEOUT` sessions (427 `PLAY` rows over 2026-11-04 and 2026-11-05) are not counted as success.
- `event_start` and the debug-event `datetime` were assumed to share the same timezone (UTC); this was not verified.
- The `clientid` split convention is flagged as unreconciled in `knowledge/mtn-sa-athena-bridge-keys-and-gotchas.md`; the id lengths matched device and household ids.
- Rows in `unified_sessions` were only read for 2026-11-04 and 2026-11-05.

## Next checks

- 6001 per active session from `unified_sessions`, and the same hours on 2026-11-03 as a baseline.
- Whether a 6001 session has any `unified_sessions` row, to test whether 6001 means playback never started.
- Split by app version, if the field exists in `eventdata`.
