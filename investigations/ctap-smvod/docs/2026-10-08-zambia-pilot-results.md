# Zambia (ZM) pilot run — 2026-10-01

MT-7 of `docs/plan/ctap-smvod-multitenant`: first real run of `run_pipeline.py --date 01102026 --tenant ZM --profile clarissa-insights-product` on a Zambia export from the shared Lightstep project
`mcs-go-prod-mtn-1-eu`. Row counts and error-code tables below come from `scripts/summarize_pipeline_run.py --date 01102026 --tenant ZM` (and `--tenant SA` for the comparison).

## Inputs and the busUnitId guard

- Zambia is separated from Ghana by `busUnitId == "dtunf6yo"` (`config/tenants.yaml`). The ctap and sm-vod exports are filtered on it in the Lightstep query.
- **The attribute name differs by service.** ctap spans carry `sessionInfo.busUnitId`; sm-vod spans carry `busUnitId`. Verified live on 2026-10-08: `service == "sm-vod" && busUnitId == "dtunf6yo"`
  returns 74 `SetupSession` spans for 2026-10-01 (including span `c54b10abe85871e3` / trace `0f51885a76dd4380`), while the same query on `sessionInfo.busUnitId` returns none.
- The MT-5 guard first rejected the exports because the `busUnitId` column was not in the group_by; it then needed an alias for sm-vod. Fixed in `7e38bf8` (`enforce_disambiguation(...,
  aliases=("busUnitId",))` for the SM-VOD export only; the value must still equal the tenant id).
- Export queries now group by the busUnitId column. ctap: `group_by ["http.user_agent", "lightstep.trace_id", "sessionInfo.busUnitId"]`; sm-vod: the usual list plus `"busUnitId"`.

## Row-count reconciliation

| Stage | Rows |
|---|---|
| ctap export | 74 (74 distinct trace ids) |
| smvod export | 74 (74 distinct trace ids) |
| smvod-ts export | 74 (joined on sessionId, no trace id column by design) |
| ctap ∩ smvod trace ids | 74 (none one-sided) |
| `setupsession.csv` / `setupsession_with_outcome.csv` | 74 / 74 |

Every export row is accounted for in the merged report. 66 sessions have a timestamp match; 8 are `matched (no timestamp found for sessionId)`. Athena found outcomes for 51 sessions; 23 have no
`unified_sessions` row (31%, versus 64% for SA on the same date).

## Error-code distribution

| Error code | ZM sessions | SA sessions (same date) |
|---|---|---|
| 1003 | 11 | 5 |
| E31012 | 4 | 2 |
| 6012 | 1 | — |
| 3016 | 1 | 1 |
| 6001 | — | 28 |
| 1001 | — | 3 |
| 6007 | — | 3 |

ZM: 17 of 74 sessions carry an error code (23%); SA: 41 of 446 (9%). `playback_outcome` for ZM: DESTROY 21, PLAYER_ERROR 15, TIMEOUT 9, EBVS 3, INCOMPLETE_NO_DESTROY 3, blank 23. The 1xxx/6xxx error
report has 12 rows, the position report 5, the WebView device report 10 wv sessions.

## Caveats

- **No Ghana comparison.** The story asks for a sanity check against Ghana, but there is no Ghana export in the repo. SA (a dedicated project) is used as the reference instead; this is a different
  tenant, so the distribution gap (1003-heavy ZM vs 6001-heavy SA) is not evidence of an error. A Ghana export for 2026-10-01 is needed to close that part of MT-7.
- One day of 74 sessions is a small sample; the ZM percentages are indicative only.
- The 1003-heavy mix and the 23 outcome-missing sessions are unexplained here and were not investigated.
