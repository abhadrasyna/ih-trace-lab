# Knowledge: MTN SA Athena Bridge Keys and Gotchas

## Read this first when

Consult this before writing a new Athena query against `unified_e6auj7k7` for an MTN SA case, or before trusting a ticket's Household ID or Device ID fields at face value.

## Known bridge keys

- Table `unified_e6auj7k7.unified_sessions` uses `parent_session_id` for the playback `sessionId`, `user_id` for Household ID, and `device_id` for Device ID.
- In `unified_sessions`, the row with `event_type = 'PLAY'` is the session-summary row, and its `endreason` is the real playback outcome.
- Table `unified_e6auj7k7.e6auj7k7_ccl_debug_events` carries failure detail that `unified_sessions` does not: `eventid = 'PLAYER_ERROR'` rows expose `errorcode` and `errordescription`.
- `e6auj7k7_ccl_debug_events` has no first-class `device_id` column. The working convention in the source notes is to filter by `clientid`, then split it client-side into `<deviceId>:<householdId>`;
  that split-index convention is still an open/unreconciled gotcha, not a settled schema guarantee.

## HAR-derived Device ID recovery gotcha

Three separate Applause issues confirmed the same pattern: when the ticket or CSV export omitted the Device ID, the value could still be recovered from the HAR's CDN MPD URL `deviceId` query
parameter.

- **7231547** — Device ID `bbcf65bd5e32038ade5606c4f76b330e80f84b22bfc73901279dddf9b08cfb29` was recovered from the MPD URL even though it was missing from the Applause export.
- **7231763** — Device ID `e3d16e00d305bc6cd858fd8cb9897717235b302a26c8099439eb14bde4be5eda` was resolved from the HAR CDN MPD URL, not from the original ticket metadata.
- **7231859** — Device ID `2d2ddaa143844e08284dbab0c9910614ff8d83627f7d85fac8baf546a2b8c6fc` was recovered from the HAR CDN MPD URL and later shown to match the value mistakenly placed in the CSV
  Household-ID column.

**Action:** if the ticket metadata is missing or suspect, recover the Device ID from the HAR's CDN MPD URL before writing Athena filters.

## Cross-tenant Household ID collision caution

Issue 7231547 also confirmed a separate hazard: a loose OR filter across household/device identifiers pulled in a row for an unrelated household/tenant.

- Target household: `I-LEiL3n3_dTCI_cUTztOZ4VoMlSy_lkOFEP7Pfhu4GODWcLomR3`
- Unrelated row surfaced during exploration: `11de5f09da8b5fe22a8497dae6001fbb488529799167a12e489c9e53d84ac4d2`

**Action:** always scope Athena queries with both Household ID and Device ID together; do not rely on a loose OR over one identifier alone.

## Related SQL shapes

The actual SQL query shapes that use these bridge keys belong to the separate `query-catalog` story's `queries/athena/` output. This file records only schema semantics and investigation gotchas, so it
does not duplicate those SQL blocks here.

## Source

Source paths: `/Users/abhadra/github_copilot/applauseInvestigation/investigations/queries/QUERY_CATALOG.md` ("Known bridge keys") and
`/Users/abhadra/github_copilot/applauseInvestigation/investigations/docs/{7231547-android-secure-decoder-failure,7231763-android-resume-watching-latency,7231859-android-micro-drama-e7504}.md`. These
files are read-only reference, not a shared codebase.
