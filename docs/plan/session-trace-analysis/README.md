# Session trace analysis — epic index

> Deliver an analysis, similar to the ZA `output/ZA/drm-analysis` reports, that follows a `sessionId` from its creation in `sm-vod` or `sm-linear` to wherever it fails. It is one epic because the
> analysis only works once every session type is captured, and the later reporting stories build on the data foundation laid first.

## Why this epic exists

The ZA DRM analysis (`investigations/ctap-smvod/output/ZA/drm-analysis`: funnel, mDRM license-chain quality, mDRM device/policy) starts from sessions already merged by `run_pipeline.py` and joins DRM
exports onto them. The goal now is the reverse direction: start at session creation, in SM-VOD or linear, and follow one `sessionId` through each hop until it fails, then aggregate that into a
funnel-style report. Discussion on 2026-10-26 found the first blocker: the Lightstep export behind the pipeline is `sm-vod` only, so linear sessions are not measured (they show up as `ctap_only` rows
or are missing). That defect is `linear-session-coverage/`; it blocks GH and ZM, not ZA VOD.

## Scope decisions

- `linear-session-coverage/` fixes linear coverage and must be **tenant-agnostic**: no hardcoded tenant lists in code; tenant ids come from `config/tenants.yaml`. Linear is confirmed possible in
  Zambia (ZM) and Ghana (GH); South Africa (ZA) may adopt it later and must work without code changes (confirmed with the user, 2026-10-26).
- `sessionId` prefix (`abr-vod-` / `abr-linear-`) is the session-type signal; `scripts/lib/drm_funnel.py::session_kind` is the existing helper.
- The per-session timeline and the first-failing-hop report are `session-lifecycle-report/` (added 2026-10-26). The `sessionId` key map (CTAP joins only via `lightstep.trace_id`; everything else via
  `sessionId`) is recorded in `session-presence-funnel/prompt.md`.
- Hop order in time (ZA 2026-10-24, checked 2026-10-26): **setup (CTAP is the same trace) ≈ debug CREATE → mdrmfe → LRM → CDM → playback → end**. Setup → CREATE median is −0.07 s, so CREATE is not a
  later hop; CREATE → mdrmfe median is 2.3 s (fcId-prefix time, a proxy). `unified_sessions` is a record derived from debug events, not a hop.
- Linear blocks GH and ZM only: over 2026-10-21..24 the mDRM exports hold 1,767 (GH) and 110 (ZM) `abr-linear-` rows and 0 for ZA (8,633 `abr-vod-` rows), so ZA VOD work does not wait for LC.

## Stories

| Story | Purpose | Status | Depends on | Closing SHA |
|---|---|---|---|---|
| `session-error-model/` | One first-error rule and one cross-day per-session outcome split (VSF, EBVS, VPF, VPT, no-end classes) | ⬜ Not started | — | — |
| `linear-session-coverage/` | Cover linear sessions in the ctap-smvod export, merge and reports (tenant-agnostic); blocks GH/ZM only | ⬜ Not started | — | — |
| `session-presence-funnel/` | Daily count of Lightstep sessions reaching Athena `unified_sessions` and debug states | ⬜ Not started | `session-error-model/`; LC-2 for the linear split only | — |
| `session-lifecycle-report/` | Daily per-tenant lifecycle summary: furthest hop, paths, hop timing, cohorts, export completeness | ⬜ Not started | EM-2, EM-4, PF-4, PF-8; LC-2 for GH/ZM | — |

Status: ⬜ Not started · 🔄 In progress · ✅ Done. This column is the epic's progress view — per-task checkboxes live only in each sub-story's `tasks.md`.

## Cross-cutting constraints

- Athena rows for a day keep arriving for days afterwards (10-05 rows were still ingested on 10-25), so any daily count is a snapshot; reports record the export time and baselines carry a tolerance.
- "Missing" always means "not observed in the Athena export"; cause is unproven unless a story proves it.

- Generic by default: tenant-specific values (busUnitId, project, filters) come from `config/tenants.yaml` via `scripts/resolve_tenant.py`; never hardcode a tenant code or id in a script.
- VOD-only outputs must stay unchanged unless a story states otherwise.
- Lightstep re-exports are a manual step; scripts never call Lightstep directly.
- Every tenant/day gets an export-completeness status (`complete`, `partial`, `unusable`; SL-1). Partial days show counts but no rates. Known cases: ZA 2026-10-21 mDRM LRM/CDM cover only 18:42–23:49
  (unusable for mDRM rates); GH 2026-10-24 mdrmfe starts 12:01; `smvod-ts` parts cap at ~499 rows and CDM at ~1,000 (ZA 2026-10-24 Widevine CDM stops at 22:56).
- The report day is the UTC day of the Athena partition, stated in every report.
- Rates on fewer than a minimum count of sessions are suppressed (default 30, a report parameter); ZM has ~100–200 VOD sessions a day.

## Supersession / coordination

Builds on the archived `ctap-smvod-multitenant` story (`docs/archive/ctap-smvod-multitenant/`) and the DRM analysis scripts in `investigations/ctap-smvod/scripts/`. No other epic is superseded.

## Epic done when

- **linear-session-coverage** — a re-exported day for every tenant with linear runs through the pipeline with linear sessions matched, typed, and reported, with no per-tenant code.
- **session-error-model** — one pure first-error rule and one cross-day outcome classifier reproduce the ZA 2026-10-24 per-session split (3,805 attempts at the first 2026-10-26 live check; 3,808 at
  17:39 IST, +3 VSF, consistent with late ingest but not verified) and print a reconciliation line against the adoption report.
- **session-presence-funnel** — one command produces the daily presence funnel for any tenant and date, reproduces the ZA 2026-10-24 baseline, and feeds a trend file checked every day.
- **session-lifecycle-report** — the daily pipeline writes one lifecycle summary per tenant with exports (ZA, GH, ZM today; NG once exported), reproduces the ZA 2026-10-24 baseline, and upserts a
  lifecycle trend row.
