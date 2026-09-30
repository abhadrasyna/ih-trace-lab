# Knowledge: MTN Adoption Playback-Outcome Classification Gap

## Read this first when

Consult this before trusting `unified_sessions`-derived adoption metrics (`vsf_unique_hhid`, `ebvs_unique_hhid`, or any `playback_outcome` column) at face value, or before writing a new per-session
`playback_outcome` classification query against `unified_e6auj7k7`.

## Adoption-report definitions and the shared root-cause query

The adoption reporting docs use four key session/outcome definitions:

- **Attempts** — a `REQUEST_VIEWING` event exists.
- **Success** — a `PLAY` event exists and ends with `endreason = 'DESTROY'`.
- **VSF** — a `REQUEST_VIEWING` event ends with `endreason = 'PLAYER_ERROR'`.
- **EBVS** — the derived `playback_outcome` says no `PLAY` happened, but a `DESTROY` event did.

The shared per-session classification query behind the `playback_outcome` field is:

```sql
COALESCE(
  MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
  CASE
    WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1 THEN 'EBVS'
    ELSE 'INCOMPLETE_NO_DESTROY'
  END
) AS playback_outcome
```

## The classification gap

That `COALESCE` never inspects `REQUEST_VIEWING.endreason`. A genuine VSF has no `PLAY` row and no `DESTROY` row, so it silently falls through to `INCOMPLETE_NO_DESTROY` even though the separate
`vsf_unique_hhid` / `vsf_sessions.py` metric counts it correctly as a request-stage failure.

The confirmed Sept-2026 misclassified or otherwise uncounted buckets were:

| Bucket | Sessions | Households | Why it falls through |
| --- | --- | --- | --- |
| `INCOMPLETE_NO_DESTROY` | 460 | 171 | Mix of genuine VSF rows and still-in-progress / no-terminal-event sessions |
| `PLAY` + `PLAYER_ERROR` | 54 | 31 | Mid-playback failures; `vsf_unique_hhid` only inspects `REQUEST_VIEWING` |
| `PLAY` + `TIMEOUT` | 2 | 2 | Another post-start failure bucket not counted by Success / VSF / EBVS |

## Confirmed examples

### Mislabeled VSF

`abr-vod-e55ef9e4-a9d4-4b13-8ce4-3f2fb504c86e` (`Cleaning House`, 2026-09-15) is returned by the per-session query as `INCOMPLETE_NO_DESTROY`, but its underlying `unified_sessions` rows show only
`REQUEST_VIEWING` with `endreason = 'PLAYER_ERROR'`. That makes it a genuine VSF and confirms the gap above.

### Genuine `INCOMPLETE_NO_DESTROY`

The stricter triple-negative filter that excludes any `PLAY`, any `DESTROY`, and any `REQUEST_VIEWING` `PLAYER_ERROR` rows still leaves genuinely incomplete sessions behind, including:

- `abr-vod-229c6f5c-...` (`Again`)
- `abr-vod-64b770de-468b-4fb7-8fd3-af7d187cff30` (`Twisted Fates`)

The 2026-09-10 reconciliation then cross-checked the originally unexplained sessions against `e6auj7k7_ccl_debug_events` by `json_extract_scalar(eventdata, '$.sessionid')` and found ongoing player
activity (`PLAYER_BUFFER_LEVEL`, `PLAYER_STATE_CHANGE`, `APP_KEEPALIVE`), with one reaching `PLAYER_EOF`. In other words, those rows were still in progress at capture time, not hidden failures.

## Candidate fix (documented, not applied)

The source docs record a candidate correction, but it has **not** been applied to any production query or reporting script yet:

```sql
COALESCE(
  MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
  CASE
    WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1 THEN 'EBVS'
    WHEN MAX(CASE WHEN event_type = 'REQUEST_VIEWING' AND endreason = 'PLAYER_ERROR' THEN 1 ELSE 0 END) = 1 THEN 'VSF'
    ELSE 'INCOMPLETE_NO_DESTROY'
  END
) AS playback_outcome
```

Treat this as a documented caveat and candidate direction, not an already-landed fix.

## Related, not yet harvested

`ctap-smvod-session-report/queries/athena_session_outcome.md` §8 uses the same unfixed `COALESCE` shape for its production `playback_outcome` column, so it shares this exact gap. That folder gets its
own harvest task later; this file only flags the dependency.

## Source

Source paths: `/Users/abhadra/github_copilot/aws-access-cli/docs/2026-09-10-adoption-session-reconciliation.md`,
`/Users/abhadra/github_copilot/aws-access-cli/docs/2026-09-15-adoption-metrics-column-overview-and-gap-analysis.md`, and
`/Users/abhadra/github_copilot/aws-access-cli/docs/2026-09-16-vsf-ebvs-session-examples-and-classification-gap.md`. These files are read-only reference, not a shared codebase.
