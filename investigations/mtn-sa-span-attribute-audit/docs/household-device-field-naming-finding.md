# Finding — why `householdId`/`deviceId` vs. `logHouseholdId`/`logDeviceId` differ across ctap spans

## The question

`sample-span-ctap-server.md` (API `shared_content`) carries `sessionInfo.logHouseholdId`/`sessionInfo.logDeviceId`. `sample-span-households-core-server.md` (`households-core` service, API
`addUserProfile`) carries plain `sessionInfo.householdId`/`sessionInfo.deviceId` (no `log` prefix). Is this a per-service naming difference, a guest-vs-authenticated-session difference, or something
else?

## Answer

**It's determined by the specific `request.api` operation, not by service or by `sessionInfo.guestMode`.** Within `ctap` itself, exactly 3 "shared" (anonymous-catalogue) APIs — `shared_content`,
`categorySpecific`, `sharedAsset` — emit `sessionInfo.logHouseholdId`/`sessionInfo.logDeviceId` instead of the standard `sessionInfo.householdId`/`sessionInfo.deviceId` that every other sampled `ctap`
API (31 others seen) and `households-core` both use. The two field sets have **zero overlap** across `request.api` values — no API emits both or switches between them.

`sessionInfo.guestMode` correlates but does **not** cleanly predict it: `guestMode=1` (anonymous) sessions are 89.3% `logHouseholdId`/10.7% `householdId`, but `guestMode=0` (authenticated) sessions
are a 33/67 split, not 100% `householdId` as a guestMode-only theory would predict — because authenticated users still call the shared `shared_content`/`categorySpecific`/`sharedAsset` APIs sometimes
(e.g. browsing a shared/public catalogue section while logged in). The `request.api` split is the clean, zero-overlap signal; `guestMode` is a correlated but noisier proxy for the same underlying
cause (these 3 APIs are the ones designed to work without a resolved household/device identity, so they log a different, lighter-weight identifier instead of the real `sessionInfo.householdId`).

## Queries run (Lightstep MCP `query_timeseries`, project `mcs-go-prod-iye9omdf-eu`, window
2026-10-05T00:00:00Z–2026-10-06T10:00:00Z)

Baseline — total `ctap` server-span volume by `guestMode`:
```
spans count | delta | filter service == "ctap" && span.kind == "server" | group_by ["sessionInfo.guestMode"], sum
```

Presence of each household field, by `guestMode` (run once per field):
```
spans count | delta | filter service == "ctap" && span.kind == "server" && defined(sessionInfo.householdId) | group_by ["sessionInfo.guestMode"], sum
spans count | delta | filter service == "ctap" && span.kind == "server" && defined(sessionInfo.logHouseholdId) | group_by ["sessionInfo.guestMode"], sum
```

Presence of each household/device field, by `request.api` (the query that produced the clean answer — run once per field):
```
spans count | delta | filter service == "ctap" && span.kind == "server" && defined(sessionInfo.householdId) | group_by ["request.api"], sum
spans count | delta | filter service == "ctap" && span.kind == "server" && defined(sessionInfo.logHouseholdId) | group_by ["request.api"], sum
spans count | delta | filter service == "ctap" && span.kind == "server" && defined(sessionInfo.deviceId) | group_by ["request.api"], sum
spans count | delta | filter service == "ctap" && span.kind == "server" && defined(sessionInfo.logDeviceId) | group_by ["request.api"], sum
```

To re-run and get a fresh CSV: use the Lightstep UI's notebook chart export (per `knowledge/mtn-sa-lightstep-query-templates.md` convention), or re-run each query via the
`synamedia-mcp-hub-lightstep_lightstep-eu_query_timeseries` MCP tool and sum each series' `points` by `group-labels` (same aggregation this finding's CSVs used).

## CSVs saved

- `data/lightstep/ctap-household-device-field-naming-by-api.csv` — one row per `request.api`, with which field name (`sessionInfo.householdId` vs. `sessionInfo.logHouseholdId`, `sessionInfo.deviceId`
  vs. `sessionInfo.logDeviceId`) that API uses and its span count over the window. This is the zero-overlap evidence.
- `data/lightstep/ctap-household-field-naming-by-guestmode.csv` — `sessionInfo.guestMode` (`1`/`0`/undefined) vs. total server-span count and `householdId`/`logHouseholdId` presence
  counts/percentages. This is the "guestMode correlates but doesn't cleanly predict it" evidence.

## Caveat

This only covers `ctap`. `households-core`'s `addUserProfile` sample never showed a `log`-prefixed variant in this sample, but a full per-API breakdown for `households-core`/other services wasn't run
— if a future investigation needs that, repeat the `request.api`-grouped queries above with `service == "households-core"` (note: `households-core` tags don't use the `sessionInfo.*` prefix the same
way — check actual tag names on a sample span first via `get_stored_trace`, e.g. `householdId` directly in that trace's other spans, rather than assuming `sessionInfo.householdId` applies there too).
