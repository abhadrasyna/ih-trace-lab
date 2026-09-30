# Knowledge: MTN SA Playback-Outcome and Error Taxonomy

## Read this first when

Consult this before interpreting a `playback_outcome`, `state_sequence`, or `error_codes` value from `unified_e6auj7k7` data, or before writing a new query against `e6auj7k7_ccl_debug_events`
`PLAYER_ERROR` / `APP_KEEPALIVE` events.

## Playback-outcome values

| Value | Meaning |
| --- | --- |
| `DESTROY` | Playback started and ended cleanly. |
| `PLAYER_ERROR` | Playback failed after a `PLAY` event; use `error_codes` / `error_descriptions` for detail. |
| `EBVS` | Request accepted, but playback never reached `PLAY` and a `DESTROY` event still occurred. |
| `INCOMPLETE_NO_DESTROY` | No clean terminal `DESTROY` was seen; this is the ambiguous bucket. |
| *(blank)* | No `unified_sessions` data matched that session for the day. |

`outcome_match_status` values describe whether the session had a matching `unified_sessions` row at all. This taxonomy is intentionally descriptive only. The query that produces these values has a
confirmed VSF-misclassification gap; see `knowledge/mtn-adoption-playback-outcome-classification-gap.md` instead of duplicating that analysis here.

## `state_sequence` lifecycle convention

`state_sequence` is a chronological, arrow-joined lifecycle string such as:

```text
CREATE->BUFFERING->PLAYING->BUFFERING->ERROR(1003)->DESTROY->STOPPED
```

Errors render inline at the point they occurred, which makes the string useful for spotting stalls, flapping, or out-of-order lifecycles at a glance.

### `APP_KEEPALIVE` position-unit gotcha

One event type breaks the usual position-unit convention: `APP_KEEPALIVE.position` is milliseconds, while the other event types use seconds. The existing conversion point is
`scripts/merge_session_outcome.py`'s `parse_position_seconds()` logic; any fresh query or parser against raw `e6auj7k7_ccl_debug_events` needs to preserve that distinction.

## `PLAYER_ERROR` raw `eventdata` schema

Two shapes can coexist:

- **Older shape** — a flatter row where `errordescription` is largely a string.
- **Newer shape** — a nested object that also carries `shakaerror` detail and `playerstatesnapshot`.

Do not assume every `PLAYER_ERROR` row exposes the nested fields.

### Confirmed relationships

- `errorcode` matches `shakaerror.code` for almost every sampled row.
- The confirmed exception in the 27 Jul 2026 sample was 3 out of 48 rows where the app-level code stayed string-only.
- The nested `shakaerror` object carries Shaka's `category`, `severity`, `code`, and `message` taxonomy; use Shaka's own `shaka.util.Error` API docs for the canonical enum meaning rather than
  re-documenting the library here.

### `playerstatesnapshot`

`playerstatesnapshot` preserves the HTML5 `<video>` element state at the moment of failure.

| Field | Meaning |
| --- | --- |
| `readystate` | `0` = `HAVE_NOTHING`, `1` = `HAVE_METADATA`, `2` = `HAVE_CURRENT_DATA`, `3` = `HAVE_FUTURE_DATA`, `4` = `HAVE_ENOUGH_DATA` |
| `networkstate` | `0` = `NETWORK_EMPTY`, `1` = `NETWORK_IDLE`, `2` = `NETWORK_LOADING`, `3` = `NETWORK_NO_SOURCE` |

This is what lets the same `errorcode` be classified as either a startup failure (`readystate = 0`, `networkstate = 3`, paused) or a mid-playback failure (`readystate = 4`, `networkstate = 2`, not
paused) without reconstructing the whole session first.

## Missing-row methodology (`no unified_sessions row`)

When a session is "missing," split the investigation into two buckets instead of treating the percentage as one monolith:

1. **Has debug events but no `unified_sessions` row** — look in `e6auj7k7_ccl_debug_events` first; the session may still have usable lifecycle evidence.
2. **No trace anywhere** — then check partition/day-boundary issues, ingestion gaps, or capture-window mismatch.

Always report the mix, not just the overall percentage. The day-boundary / partition-cutoff check is part of the standard method.

## `householdId` anomaly-scan gotcha

The normal household-id shape is an opaque token about 52 characters long. A separate anomaly class shows raw identity-provider strings instead, such as `google-oauth2|<id>`.

When these non-standard household IDs appear:

- flag them as unresolved identity strings rather than resolved household IDs;
- compare them against the platform breakdown, because they can explain an otherwise "zero DESTROY" platform by themselves; and
- check whether multiple anomalous IDs share the same client IP, which is a strong signal of a shared test/lab rig rather than genuine customer traffic.

## Source

Source path: `/Users/abhadra/github_copilot/ctap-smvod-session-report/{LEGEND.md,BLUEPRINT.md,analyze_playback_outcome.md}`. These files are read-only reference, not a shared codebase.
