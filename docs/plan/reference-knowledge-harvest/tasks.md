# Reference knowledge harvest — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec. This list grows: a new `RKH-N` gets appended each time another `github_copilot/*` folder is next up for harvesting — don't assume RKH-1/RKH-2 (the `vod-asset-ingestion-mapping/` batch) is the
whole story.

**Open: RKH-1, RKH-2, RKH-3, RKH-4, RKH-5, RKH-6.**

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

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per your project's own convention — do not leave a done story half-archived.
