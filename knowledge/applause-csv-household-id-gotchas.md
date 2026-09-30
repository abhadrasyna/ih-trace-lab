# Knowledge: Applause CSV Household-ID Gotchas

## Read this first when

Consult this before trusting any `Household ID` or `Device ID` field from an Applause-style CSV export at face value, or before inferring "same household" from a partial string match.

## "Household ID" column can actually contain the Device ID

Seen on issue **7231859**: the CSV's `Household ID` field was `2d2ddaa143844e08284dbab0c9910614ff8d836 27f7d85fac8baf546a2b8c6fc` — two space-separated tokens. Concatenating them (removing the space)
produced an **exact match** for the Device ID independently recovered from the HAR's CDN MPD URL (`scripts/analyze_har.py sessions`). This means the export had put the Device ID into the Household ID
column, split by a stray space — not two genuine identifier halves, and not a usable Household ID at all.

**Action:** if a ticket's `Household ID` field looks malformed (unexpected space, wrong length/format vs. other tickets), check whether it actually matches the Device ID recoverable from that ticket's
HAR before using it in any Athena/Lightstep query. Don't assume it's a two-part household identifier.

## Household ID prefix similarity is NOT a same-household signal

Seen across issues **7231859**, **7232657**, and **7232351**: 7231859's real Household ID (`yK3cA9Wt3P5HKXmcO3bthy66C44HCFBwxSHPquClcvrYT3eLwit4`) shares the same 42-character prefix
(`yK3cA9Wt3P5HKXmcO3bthy66C44HCFBwxSHPquClc`) with the Household ID on record for 7232657/7232351 (`yK3cA9Wt3P5HKXmcO3bthy66C44HCFBwxSHPquClc_bQSHaGzi54`) — only the last ~10-11 characters differ.
This was **confirmed to be a different household**, not a shared account, despite the strong prefix match.

**Action:** don't infer "same household" from a partial/prefix match on a Household ID string in this scheme — always confirm via an independent signal (Lightstep
`sessionInfo.householdId`/`householdId` on an actual matching trace, or explicit confirmation) before treating two tickets as the same account/household.

## Source

Source path: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/applause-csv-household-id-gotchas.md`. Provenance issues: 7231859, 7232657, 7232351. The source path is read-only reference,
not a shared codebase.
