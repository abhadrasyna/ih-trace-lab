# Reference knowledge harvest — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec. This list grows: a new `RKH-N` gets appended each time another `github_copilot/*` folder is next up for harvesting — don't assume RKH-1/RKH-2 (the `vod-asset-ingestion-mapping/` batch) is the
whole story.

**Open: RKH-1, RKH-2, RKH-3, RKH-4, RKH-5, RKH-6, RKH-7, RKH-8, RKH-9, RKH-10, RKH-11, RKH-12, RKH-13, RKH-14, RKH-15, RKH-16.**

- [ ] **RKH-1** — `knowledge/vod-asset-field-mapping.md`: harvest ID-navigation + field-mapping docs from `vod-asset-ingestion-mapping/` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 |
  Review: human diff review | SHA: <—>
- [ ] **RKH-2** — `knowledge/vod-asset-ingestion-pipeline.md` + `knowledge/ctap-smvod-pipeline.md`: port + correct root `knowledge/` distillations, add applauseInvestigation pointer | Owner: AI agent
  (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-3** — `knowledge/mtn-sa-lightstep-span-attributes-by-service.md`: harvest `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` | Owner: AI agent (Copilot CLI) | Model:
  claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-4** — `knowledge/mtn-sa-lightstep-query-templates.md`: harvest `applauseInvestigation/knowledge/lightstep-query-templates.md` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 |
  Review: human diff review | SHA: <—>
- [ ] **RKH-5** — `knowledge/applause-csv-household-id-gotchas.md`: harvest `applauseInvestigation/knowledge/applause-csv-household-id-gotchas.md` | Owner: AI agent (Copilot CLI) | Model:
  claude-sonnet-5
  | Review: human diff review | SHA: <—>
- [ ] **RKH-6** — `knowledge/mtn-sa-service-correlation-maps.md` (new) + `knowledge/ctap-smvod-pipeline.md` (edit): port + cross-link root distillations that share span/field names with
  `applauseInvestigation` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—> | Depends on: RKH-2 (creates `ctap-smvod-pipeline.md`), RKH-3 (creates the
  span-attributes file this task cross-links to)
- [ ] **RKH-7** — `knowledge/mtn-sa-athena-bridge-keys-and-gotchas.md`: harvest `applauseInvestigation/investigations/queries/QUERY_CATALOG.md`'s "Known bridge keys" section + the HAR-derived Device
  ID recovery gotcha from `applauseInvestigation/investigations/docs/*.md` — the `investigations/` subfolder missed by the RKH-3–6 spec pass | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 |
  Review: human diff review | SHA: <—>
- [ ] **RKH-8** — `knowledge/mtn-adoption-playback-outcome-classification-gap.md`: harvest
  `aws-access-cli/docs/{2026-09-10-adoption-session-reconciliation,2026-09-15-adoption-metrics-column-overview-and-gap-analysis,2026-09-16-vsf-ebvs-session-examples-and-classification-gap}.md`
  | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-9** — `knowledge/mtn-athena-unified_e6auj7k7-tables.md` (edit): cross-link to RKH-8's new file | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA:
  <—> | Depends on: RKH-8 (creates the file this task links to)
- [ ] **RKH-10** — `knowledge/mtn-sa-playback-outcome-and-error-taxonomy.md`: harvest `ctap-smvod-session-report/{LEGEND.md,BLUEPRINT.md,analyze_playback_outcome.md}`'s `playback_outcome`/
  `state_sequence`/`PLAYER_ERROR` error-schema/`householdId`-anomaly findings | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-11** — `knowledge/mtn-sa-cdn-log-correlation-methodology.md`: harvest `ctap-smvod-session-report/LEGEND.md`'s "CDN log fields" section + `docs/STATUS.md`'s MTN escalation criteria | Owner:
  AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-12** — `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md`: harvest the four undocumented 2026-07-24 docs from root `investigations/docs/` (MTN SA 4032 DRM flow, TIM Play mileto
  trace, MTN-vs-TIM-Play comparison, TIM Play tenant-config/LTV analysis) | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-13** — `knowledge/mtn-tenant-identifiers-and-code-flow.md`: harvest root `investigations/docs/ITZUu4aBswL.md` + `_code_flow.md` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 |
  Review: human diff review | SHA: <—>
- [ ] **RKH-14** — port `github_copilot/knowledge/{ctap-shared-content-default-limit,mpd-shaka-restrictions-analysis,recommendation-engine-thinkanalytics}.md` into `ih-trace-lab/knowledge/` | Owner:
  AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—> | Depends on: RKH-12 (creates the file these ports cross-link to)
- [ ] **RKH-15** — `knowledge/mtn-lightstep-identity-and-session-investigation-methodology.md`: distill root `investigations/instructions/{lightstep-mcp-tool-notes,client-identity-investigation,
  device-flow-analysis,oauth-session-guard-interleave,drm-cross-region-investigation}.md` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RKH-16** — `knowledge/mtn-har-kinesis-and-manifest-analysis-methodology.md`: distill root `investigations/instructions/{har-playback-flow-analysis,kinesis-stream-analysis,mpd-analysis,
  device-ua-playsession-analysis}.md` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—> | Depends on: RKH-14 (creates the ported
  `mpd-shaka-restrictions-analysis.md` this task cross-links to instead of duplicating)

## Story done when

- **RKH-1** — `knowledge/vod-asset-field-mapping.md` exists, contains the four-ID-family navigation table (Physical Content ID / Internal Content ID / Package Asset ID / Show-Season ID) and the
  ADI→`contentInstances`→MongoDB field correspondence tables, plus a short note on the auto-generated `common-field-mapping*.md` matrix and where to find it if a fresher regeneration is ever needed
  (without porting the generator scripts themselves).
- **RKH-2** — `knowledge/vod-asset-ingestion-pipeline.md` and `knowledge/ctap-smvod-pipeline.md` both exist in `ih-trace-lab`, the MongoDB "open gap" claim in the former is corrected to reflect
  `STATUS.md`'s stage-6 closure, both cross-link to `knowledge/vod-asset-field-mapping.md` instead of repeating its tables, and `vod-asset-ingestion-pipeline.md` carries one clearly-labeled pointer to
  `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` marked as not-yet-harvested / deferred to a future `applauseInvestigation`-scoped story.
- **RKH-3** — `knowledge/mtn-sa-lightstep-span-attributes-by-service.md` exists, preserves every per-service tag/attribute finding from the source file (universal fields, `session-guard`'s
  snake_case/near-zero-duration gotchas, `sm-vod`/`sm-linear`/`sm-tstv`/`ctap`/`channellineup`/`households-*` fields, known noise, group-by recommendations), generalizes the framing beyond the single
  Applause issue it was built from, and notes the 4 services (`vodcontent-get`, `favm`, `viewinghistory-viewing-history`, `tstv-capture-bc`) named in `mtn-sa-service-correlation-maps.md` as not yet
  covered here — without pulling data from `vod-asset-ingestion-mapping/`'s trace JSONs to fill that gap (out of scope per the scope guard: one source folder per task).
- **RKH-4** — `knowledge/mtn-sa-lightstep-query-templates.md` exists, preserves every reusable query shape from the source file (Big Picture, sm-vod Session Inventory, latency templates incl. the FCID
  exact-trace-pull technique, session-guard request-vs-upstream, go-mdrmfe EU latency), and cross-links to `knowledge/mtn-sa-lightstep-span-attributes-by-service.md` (RKH-3) for tag-name lookups
  instead of repeating them.
- **RKH-5** — `knowledge/applause-csv-household-id-gotchas.md` exists and preserves both data-quality findings (Household-ID-column-actually-contains-Device-ID; prefix-similarity-is-not-a-same-
  household-signal) with their confirmed/refuted framing intact.
- **RKH-6** — `knowledge/mtn-sa-service-correlation-maps.md` exists in `ih-trace-lab` (ported from the root distillation), its §4 "no edges" `session-guard` entry is annotated with a cross-link to
  RKH-3's detailed session-guard findings instead of listing it as unexplained, and `knowledge/ctap-smvod-pipeline.md` (created by RKH-2) gains a cross-link to RKH-3/RKH-4 for `ctap`/`sm-vod` tag- and
  query-level detail — no field-table duplication introduced between the three files.
- **RKH-7** — `knowledge/mtn-sa-athena-bridge-keys-and-gotchas.md` exists, preserves the `unified_sessions`/`e6auj7k7_ccl_debug_events` bridge-key/schema semantics from `QUERY_CATALOG.md`'s "Known
  bridge keys" section, adds the HAR-derived Device ID recovery gotcha (citing 7231547/7231763/7231859) and the cross-tenant Household ID collision caution (citing 7231547), states the SQL query
  shapes themselves are out of scope (pointing to the `query-catalog` story's QC-2 output instead, no duplication), and leaves `investigations/docs/*.md`'s remaining case write-ups and
  `investigations/README.md`'s folder-org convention untouched as out of scope.
- **RKH-8** — `knowledge/mtn-adoption-playback-outcome-classification-gap.md` exists, preserves the shared `playback_outcome` `COALESCE` classification query, the VSF-misclassification gap it causes
  (VSF sessions silently folded into `INCOMPLETE_NO_DESTROY`), the confirmed monthly counts (460/171 `INCOMPLETE_NO_DESTROY`, 54/31 `PLAY`+`PLAYER_ERROR`, 2/2 `PLAY`+`TIMEOUT`), one session-level
  example of a mislabeled VSF and one of a genuinely-incomplete session, the not-yet-applied candidate fix, and a "Related, not yet harvested" pointer to `ctap-smvod-session-report`'s identical-gap
  query — without duplicating any SQL belonging to the `query-catalog` story.
- **RKH-9** — `knowledge/mtn-athena-unified_e6auj7k7-tables.md` gains one cross-link sentence to RKH-8's new file near its existing `unified_sessions`/`playback-outcome` mentions, with no other
  content changed and no duplication of RKH-8's findings.
- **RKH-10** — `knowledge/mtn-sa-playback-outcome-and-error-taxonomy.md` exists, preserves the `playback_outcome` value taxonomy, the `state_sequence` lifecycle-string convention and
  `APP_KEEPALIVE`-position-is-milliseconds gotcha, the `PLAYER_ERROR` raw `eventdata`/Shaka-error/`playerstatesnapshot` schema, the "missing" root-cause methodology, and the `householdId` anomaly-scan
  gotcha — without duplicating RKH-8's (not-yet-landed) VSF-misclassification gap analysis, which it only forward-points to.
- **RKH-11** — `knowledge/mtn-sa-cdn-log-correlation-methodology.md` exists, preserves the raw CDN log field reference, cache-hit/origin-fetch and `ERR_CLIENT_ABORT` interpretation, the ±5-minute
  window methodology, and the MTN escalation criteria (with its "not yet done" status flagged as time-of-writing) — cross-linked to (not duplicating) `knowledge/ctap-smvod-pipeline.md`'s existing
  content-UUID-matching algorithm pitfalls.
- **RKH-12** — `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md` exists, preserves the four 2026-07-24 docs' cross-tenant DRM/session-flow findings (MTN SA `iye9omdf` vs. TIM Play/mileto
  `iljyxcc3`, tenant identifiers, `ctap`→`sm-vod`→`go-mdrmfe`→license-server trace chain), and flags the source folder's stale case-index gap (these four docs are absent from
  `investigations/README.md`'s own case-log table) without editing the read-only source.
- **RKH-13** — `knowledge/mtn-tenant-identifiers-and-code-flow.md` exists, preserves `ITZUu4aBswL.md`/`_code_flow.md`'s tenant-ID facts and the full HAR→code-flow trace (login, VOD playback, mDRM
  Widevine license, Kinesis analytics), and forward-notes `docs/plan/tenant-registry/` as the eventual consumer once that not-yet-implemented story's resolver work begins.
- **RKH-14** — `knowledge/{ctap-shared-content-default-limit,mpd-shaka-restrictions-analysis,recommendation-engine-thinkanalytics}.md` all exist in `ih-trace-lab`, ported as-is from the root
  `github_copilot/knowledge/` originals, cross-linked to RKH-12 where their underlying case docs (DRM/manifest analysis) overlap.
- **RKH-15** — `knowledge/mtn-lightstep-identity-and-session-investigation-methodology.md` exists, distills the reusable facts/methodology (MCP query syntax hard rules, householdId→clientId resolution
  steps, device/CTAP flow tracing, OAuth⇄session-guard interleave rules, EU⇄US DRM trace-correlation technique) from its five source playbooks without porting their full executable prompt/invocation
  text.
- **RKH-16** — `knowledge/mtn-har-kinesis-and-manifest-analysis-methodology.md` exists, distills the reusable facts/methodology (HAR playback-flow reconstruction approach, Kinesis `PutRecords`
  decode/flatten rules, MPD/DASH analysis rules, device/UA CSV analysis approach) from its four source playbooks, cross-linked to RKH-14's ported `mpd-shaka-restrictions-analysis.md` instead of
  duplicating its DASH/Shaka detail.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per your project's own convention — do not leave a done story half-archived.
