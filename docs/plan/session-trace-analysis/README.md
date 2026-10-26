# Session trace analysis — epic index

> Deliver an analysis, similar to the ZA `output/ZA/drm-analysis` reports, that follows a `sessionId` from its creation in `sm-vod` or `sm-linear` to wherever it fails. It is one epic because the
> analysis only works once every session type is captured, and the later reporting stories build on the data foundation laid first.

## Why this epic exists

The ZA DRM analysis (`investigations/ctap-smvod/output/ZA/drm-analysis`: funnel, mDRM license-chain quality, mDRM device/policy) starts from sessions already merged by `run_pipeline.py` and joins DRM
exports onto them. The goal now is the reverse direction: start at session creation, in SM-VOD or linear, and follow one `sessionId` through each hop until it fails, then aggregate that into a
funnel-style report. Discussion on 2026-10-26 found the first blocker: the Lightstep export behind the pipeline is `sm-vod` only, so linear sessions are not measured (they show up as `ctap_only` rows
or are missing). That defect is the first story.

## Scope decisions

- The first story fixes linear coverage and must be **tenant-agnostic**: no hardcoded tenant lists in code; tenant ids come from `config/tenants.yaml`. Linear is confirmed possible in Zambia (ZM) and
  Ghana (GH); South Africa (ZA) may adopt it later and must work without code changes (confirmed with the user, 2026-10-26).
- `sessionId` prefix (`abr-vod-` / `abr-linear-`) is the session-type signal; `scripts/lib/drm_funnel.py::session_kind` is the existing helper.
- Later stories (not yet created, to be added as the discussion continues): an id-mapping spike across hops (`sessionId` vs `fcId`, household/device, trace id), a per-session timeline, and a
  first-failing-hop funnel report. The `sessionId` key map (CTAP joins only via `lightstep.trace_id`; everything else via `sessionId`) is recorded in `session-presence-funnel/prompt.md`.

## Stories

| Story | Purpose | Status | Depends on | Closing SHA |
|---|---|---|---|---|
| `linear-session-coverage/` | Cover linear sessions in the ctap-smvod export, merge and reports (tenant-agnostic) | ⬜ Not started | — | — |
| `session-error-model/` | One first-error rule and one cross-day per-session outcome split (VSF, EBVS, VPF, VPT, no-end classes) | ⬜ Not started | — | — |
| `session-presence-funnel/` | Daily count of Lightstep sessions reaching Athena `unified_sessions` and debug states | ⬜ Not started | `session-error-model/`, LC-2 | — |

Status: ⬜ Not started · 🔄 In progress · ✅ Done. This column is the epic's progress view — per-task checkboxes live only in each sub-story's `tasks.md`.

## Cross-cutting constraints

- Athena rows for a day keep arriving for days afterwards (10-05 rows were still ingested on 10-25), so any daily count is a snapshot; reports record the export time and baselines carry a tolerance.
- "Missing" always means "not observed in the Athena export"; cause is unproven unless a story proves it.

- Generic by default: tenant-specific values (busUnitId, project, filters) come from `config/tenants.yaml` via `scripts/resolve_tenant.py`; never hardcode a tenant code or id in a script.
- VOD-only outputs must stay unchanged unless a story states otherwise.
- Lightstep re-exports are a manual step; scripts never call Lightstep directly.

## Supersession / coordination

Builds on the archived `ctap-smvod-multitenant` story (`docs/archive/ctap-smvod-multitenant/`) and the DRM analysis scripts in `investigations/ctap-smvod/scripts/`. No other epic is superseded.

## Epic done when

- **linear-session-coverage** — a re-exported day for every tenant with linear runs through the pipeline with linear sessions matched, typed, and reported, with no per-tenant code.
- **session-error-model** — one pure first-error rule and one cross-day outcome classifier reproduce the ZA 2026-10-24 per-session split (3,805 attempts at the 2026-10-26 live check) and print a
  reconciliation line against the adoption report.
- **session-presence-funnel** — one command produces the daily presence funnel for any tenant and date, reproduces the ZA 2026-10-24 baseline, and feeds a trend file checked every day.
