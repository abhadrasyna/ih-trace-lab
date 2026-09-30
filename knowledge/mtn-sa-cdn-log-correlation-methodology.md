# Knowledge: MTN SA CDN Log Correlation Methodology

## Read this first when

Consult this before interpreting a raw CDN-team access-log export (`cdnReport/results_sa_*` style, IP + time-window blocks), or before deciding whether a playback failure is network-path, CDN, or
origin related.

## Raw field reference

Each block represents one `(IP, sessionId)` pair, and the CDN team's automation pulls exactly `session start_time - 5 min` through `start_time + 5 min`. A block with zero data rows is a meaningful
finding, not a parsing gap.

| Field | Meaning |
| --- | --- |
| `timestamp` | Time the request was logged at the CDN edge |
| `stms` | CDN-side processing / queue time before the response begins |
| `ttfb` | Time To First Byte: request receipt to first response byte |
| `ttms` | Total transaction time: request receipt to full response complete |
| `sssc` | Origin HTTP status; `0` means the CDN never contacted origin |
| `pssc` | Status code the CDN edge returned to the client |
| `crc` | Cache Result Code: `TCP_HIT`, `TCP_MEM_HIT`, `TCP_MISS`, `TCP_REFRESH_MISS`, `ERR_CLIENT_ABORT` |
| `bytes` | Response payload transferred before the request finished or aborted |
| `url` | Requested CDN URL |

## How to interpret a block

### Cache hit vs. origin fetch

- `sssc = 0` with `crc = TCP_HIT` / `TCP_MEM_HIT` means the CDN served the object from cache and never contacted origin.
- `sssc != 0` with `crc = TCP_MISS` / `TCP_REFRESH_MISS` means origin was contacted.
- In the observed origin-fetch rows, `stms == ttfb == ttms` is the tell that the total time was spent waiting on origin rather than on client transfer.
- `results_sa_20260707` confirmed the dominant pattern: roughly 2,321 of ~2,700 real data rows were pure cache hits, so origin fetches are the minority case.

### `ttfb` vs. `ttms`

- Low `ttfb` and `ttms ≈ ttfb` means healthy request/response handling.
- A large `ttfb ≈ ttms` points at slow origin response.
- A large gap between `ttfb` and `ttms` points at a slow or large transfer after the first byte, not necessarily a slow origin.

### Zero-row blocks

If the `(IP, sessionId)` block has no CDN data rows at all, the request never reached the CDN in that ±5 minute window. That is the strongest signal for a network-path issue before the CDN, not a
CDN/origin failure.

### `ERR_CLIENT_ABORT`

`ERR_CLIENT_ABORT` means the client disconnected before the CDN finished responding. Distinguish the two real-world sub-patterns by `bytes`:

| Pattern | Interpretation |
| --- | --- |
| `bytes = 0` | Client aborted before any payload was transferred; usually a benign cancel or user-navigation event |
| `bytes > 0` | CDN had already started sending data, then the connection vanished mid-transfer; suspect client/network instability rather than CDN/origin |

The confirmed `results_sa_20260707` counts were 145 `ERR_CLIENT_ABORT` rows total: **126 with `bytes = 0`** and **19 with `bytes > 0`**. Miltos Margaronis's reasoning on the second bucket was that
request and response had already succeeded, data was flowing, and only then did the connection disappear — that implicates the network path or client side, not the CDN or origin.

## The ±5 minute window matters

The fixed ±5 minute window is deliberate. It captures retries and neighbouring manifest/segment traffic for the same IP without relying on a single request timestamp. The source notes explicitly
confirm that this is an exact, stable rule rather than a rough heuristic.

## Quick classification table

| Signal | Interpretation |
| --- | --- |
| `sssc = 0` | Cache hit; origin not involved |
| `sssc != 0`, low `ttfb` | Origin contacted and responded quickly |
| `sssc != 0`, high `ttfb ≈ ttms` | Origin latency issue |
| `ERR_CLIENT_ABORT`, `bytes = 0` | Likely benign client-side cancel |
| `ERR_CLIENT_ABORT`, `bytes > 0` | Client/network disconnect mid-transfer |
| Zero CDN rows in block | Network issue before CDN |
| No CDN-side errors, only aborts | Evidence against CDN/origin as the root cause |

## MTN network-team escalation criteria (time-of-writing: 16 Jul 2026)

The source `docs/STATUS.md` recorded three trigger conditions for escalation to the MTN network team:

1. the session has **zero CDN rows** in the ±5 minute window;
2. the session has `ERR_CLIENT_ABORT` **after** data transfer had already started (`bytes > 0`); or
3. the script-level `root_cause_hint` classifies the failure as a network/app-layer issue rather than a CDN/origin issue.

The practical sequence there was:

1. collect the affected IPs, timestamps, and sessionIds;
2. run the correlation/classification flow to produce `root_cause_hint` and `mtn_escalation`;
3. send only the candidate rows, not every CDN block, to the MTN network team.

Treat the "not yet done" status in that 16 Jul 2026 note as time-of-writing only; re-check the submodule's own `docs/STATUS.md` if current escalation practice matters.

## Related algorithm-level pitfalls

This file covers raw CDN log-field semantics. `knowledge/ctap-smvod-pipeline.md` covers the separate algorithm-level pitfalls for matching sessions to CDN rows at all, including dense-burst
misattribution and shared-IP content-UUID disambiguation. Keep the two references paired, but do not duplicate their content.

## Source

Source paths: `/Users/abhadra/github_copilot/ctap-smvod-session-report/LEGEND.md` ("CDN log fields") and `/Users/abhadra/github_copilot/ctap-smvod-session-report/docs/STATUS.md` ("MTN network-team
escalation criteria", 16 Jul 2026). These files are read-only reference, not a shared codebase.
