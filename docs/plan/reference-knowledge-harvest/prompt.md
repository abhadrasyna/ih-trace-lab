# Reference knowledge harvest — prompt

> The ongoing, docs-only vehicle for pulling reusable knowledge out of `github_copilot`'s ~13 read-only investigation folders into `ih-trace-lab/knowledge/`, one folder at a time. This is not a
> one-off — new tasks (`RKH-3`, `RKH-4`, ...) get appended here each time a new source folder is next up for harvesting. The first batch (`RKH-1`/`RKH-2`) covers `vod-asset-ingestion-mapping/`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. This story has two modes — pick the one matching what you were asked to do, never both in the same session:

- **Default / execution mode** (no folder named): read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same task id) before writing
  any code. One task per session. Complete it fully. Stop.
- **Spec-authoring mode** (a `github_copilot/*` folder is named, e.g. "harvest `applauseInvestigation` next"): do **not** touch `knowledge/*.md`. Instead follow "Adding a new folder (spec-authoring
  mode)" below to append new `RKH-N` task(s) to `tasks.md`/`stories.md`. Stop once that spec is committed — do not execute the freshly-spec'd task in the same session.

## Why this story exists

Reusable facts (field mappings, gotchas, query templates, span-attribute references) accumulate across `github_copilot`'s investigation folders but stay siloed there — each is read-only reference, not
wired into `ih-trace-lab` as a submodule, so nothing crosses over automatically (see `CONTEXT.md`'s constraint: that tree is prior art, not a shared codebase). This story is the repeatable process for
closing that gap: pick one source folder, compare it against the root `github_copilot/knowledge/` files that already reference it, and land a distilled, corrected, cross-linked knowledge file here —
then move to the next folder as its own task, never bundling multiple folders into one task.

The first folder up is `vod-asset-ingestion-mapping/` (a recurring MTN SA investigation submodule): it has already built an auto-generated, value-matched field-mapping matrix tracing a VOD asset
across ADI XML → OpsHub → HAR → Lightstep spans → MongoDB → CTAP response, plus an ID-navigation cheat sheet (Physical/Internal Content ID, Package Asset ID, Show/Season ID). The root
`github_copilot/knowledge/` folder already distilled a first pass of this (`vod-asset-ingestion-pipeline.md`) plus an adjacent CTAP/SM-VOD session-correlation pipeline (`ctap-smvod-pipeline.md`,
sharing the same `ctap`/`sm-vod` spans) — both worth pulling into `ih-trace-lab` alongside a fresher pass over the submodule's own docs, since the root distillation is already stale in at least one
place (it says the MongoDB layer "hasn't started"; the submodule's own `STATUS.md` shows that layer closed out as of its "stage 6" entry).

## Scope guard

**Per-task rule (applies to every RKH task, present and future):** exactly one `github_copilot/*` source folder plus the root `github_copilot/knowledge/` files that reference it — never two
investigation folders compared/bundled in the same task. Sources are always read-only, never edited.

**This batch (RKH-1/RKH-2) — folder under harvest: `vod-asset-ingestion-mapping/`:**
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/` — specifically `docs/opshub-asset-id-mapping.md`, `docs/ctap-query-mapping.md`, `docs/mongodb-mapping.md`, `docs/STATUS.md` (for the
  stage-6 MongoDB correction), and `data/opshubs/common-field-mapping{,-overview,-details}.md`.
- `/Users/abhadra/github_copilot/knowledge/vod-asset-ingestion-pipeline.md` and `/Users/abhadra/github_copilot/knowledge/ctap-smvod-pipeline.md`.

**Not in this batch, but not out of scope for this story either — future tasks, not yet numbered:** every other `github_copilot/*` project folder (`applauseInvestigation`, `ctap-smvod-session-report`,
`astro-events-household-report`, etc.) gets its own future `RKH-N` task in this same story, scoped the same narrow way (root `knowledge/` + that one folder) once it's next up. In particular,
`applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` (a per-service Lightstep tag/attribute reference — genuinely useful for MCP querying, and it already documents
`ctap`/`sm-vod`/`session-guard`, all seen in this submodule's own traces) is **not** harvested by RKH-1/RKH-2 — RKH-2 leaves an explicit pointer to it so a future `applauseInvestigation` task (added
here, not a new story) picks it up (and can extend it with the 4 services — `vodcontent-get`, `favm`, `viewinghistory-viewing-history`, `tstv-capture-bc` — that only appear in this submodule's trace
JSONs, not in that file today). No script/`scripts/lib/` porting in this story — matrix regeneration against new assets is a separate, larger decision if ever needed. No live MCP/Athena/Lightstep
call.

## Session-start load hints

- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/opshub-asset-id-mapping.md` — the ID-navigation cheat sheet (read-only source, do not edit).
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/ctap-query-mapping.md` — ADI → CTAP response field table, incl. §5 series-specific fields (read-only source, do not edit).
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/mongodb-mapping.md` — ADI/API → MongoDB layer (read-only source, do not edit).
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/STATUS.md` — read the "series, stage 6 — MongoDB layer" entry specifically, it's the correction source for RKH-2.
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/data/opshubs/common-field-mapping-overview.md` (+ `-details.md`) — the auto-generated per-asset-class matrix (read-only source, do not
  edit).
- `/Users/abhadra/github_copilot/knowledge/vod-asset-ingestion-pipeline.md`, `/Users/abhadra/github_copilot/knowledge/ctap-smvod-pipeline.md` — the two root-level distillations being harvested
  (read-only source, do not edit).
- `/Users/abhadra/github_copilot/applauseInvestigation/investigations/queries/QUERY_CATALOG.md` — read only its "Known bridge keys" section for RKH-7; its SQL blocks belong to the separate
  `query-catalog` story, not this one (read-only source, do not edit).
- `/Users/abhadra/github_copilot/applauseInvestigation/investigations/docs/{7231547-android-secure-decoder-failure,7231763-android-resume-watching-latency,7231859-android-micro-drama-e7504}.md` — the
  three issues confirming RKH-7's HAR-derived Device ID recovery gotcha (read-only source, do not edit).
- `aws-access-cli/docs/{2026-09-10-adoption-session-reconciliation,2026-09-15-adoption-metrics-column-overview-and-gap-analysis,2026-09-16-vsf-ebvs-session-examples-and-classification-gap}.md` (under
  `/Users/abhadra/github_copilot/`) — the three dated investigation docs confirming RKH-8's `playback_outcome` classification gap (read-only source, do not edit).
- `/Users/abhadra/github_copilot/ctap-smvod-session-report/LEGEND.md`, `BLUEPRINT.md`, `analyze_playback_outcome.md` — RKH-10's playback-outcome/error-taxonomy sources; and `LEGEND.md`'s "CDN log
  fields" section + `docs/STATUS.md`'s MTN escalation criteria — RKH-11's CDN-methodology sources (all read-only, do not edit).

## Task overview

**Batch 1 (`vod-asset-ingestion-mapping/`):**
- **RKH-1** — `knowledge/vod-asset-field-mapping.md`: harvest the submodule's own docs (ID-navigation table + ADI→API→Mongo field tables + the auto-generated common-field-mapping matrix summary) into
  one distilled, ih-trace-lab-native knowledge file.
- **RKH-2** — `knowledge/vod-asset-ingestion-pipeline.md` + `knowledge/ctap-smvod-pipeline.md`: port both root `github_copilot/knowledge/` distillations, correct the stale MongoDB-gap claim,
  cross-link to RKH-1's output, and add the explicit "not yet harvested" pointer to `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`.

**Batch 2 (`applauseInvestigation/`):**
- **RKH-3** — `knowledge/mtn-sa-lightstep-span-attributes-by-service.md`: harvest the submodule's per-service Lightstep tag/attribute reference as-is, generalized beyond its single-issue framing, with
  a "not yet covered" note for the 4 services named in `mtn-sa-service-correlation-maps.md`'s call graph.
- **RKH-4** — `knowledge/mtn-sa-lightstep-query-templates.md`: harvest the submodule's generic reusable Lightstep query shapes, cross-linked to RKH-3 for tag names instead of repeating them.
- **RKH-5** — `knowledge/applause-csv-household-id-gotchas.md`: harvest the submodule's two Household-ID/Device-ID CSV data-quality findings as-is.
- **RKH-6** — `knowledge/mtn-sa-service-correlation-maps.md` (new) + `knowledge/ctap-smvod-pipeline.md` (edit, depends on RKH-2/RKH-3 landing first): port the root service-correlation-maps
  distillation and cross-link its `session-guard` "no edges" gap to RKH-3's detailed findings; cross-link `ctap-smvod-pipeline.md`'s shared `ctap`/`sm-vod` join-key facts to RKH-3/RKH-4.
- **RKH-7** — `knowledge/mtn-sa-athena-bridge-keys-and-gotchas.md`: harvest the submodule's `investigations/` subfolder (missed by the RKH-3–6 spec pass) — the Athena `unified_sessions`/
  `e6auj7k7_ccl_debug_events` bridge-key semantics from `investigations/queries/QUERY_CATALOG.md`, plus the HAR-derived Device ID recovery gotcha and cross-tenant Household ID collision caution from
  `investigations/docs/*.md`; the SQL query shapes themselves are left to the separate `query-catalog` story's QC-2 task, not duplicated here.

**Batch 3 (`aws-access-cli/`, reclassified out of the infra-folder exclusion below — the CLI/automation code itself stays excluded, but its `docs/2026-09-*.md` investigation findings do not):**
- **RKH-8** — `knowledge/mtn-adoption-playback-outcome-classification-gap.md`: harvest the submodule's three dated investigation docs on the `unified_sessions` per-session `playback_outcome`
  classification gap (VSF sessions silently folded into `INCOMPLETE_NO_DESTROY`), with a "not yet harvested" pointer to `ctap-smvod-session-report`'s identical-gap query.
- **RKH-9** — `knowledge/mtn-athena-unified_e6auj7k7-tables.md` (edit, depends on RKH-8 landing first): cross-link the existing root-ported table-schema file to RKH-8's new gap-analysis file, no
  content duplicated.

**Batch 4 (`ctap-smvod-session-report/`):**
- **RKH-10** — `knowledge/mtn-sa-playback-outcome-and-error-taxonomy.md`: harvest the submodule's own `playback_outcome` value taxonomy, `state_sequence`/`APP_KEEPALIVE` lifecycle gotchas,
  `PLAYER_ERROR` raw-eventdata/Shaka-error schema, "missing"-row investigation methodology, and `householdId` anomaly-scan gotcha from `LEGEND.md`/`BLUEPRINT.md`/`analyze_playback_outcome.md` —
  explicitly deferring the classification-gap analysis itself to `aws-access-cli`'s RKH-8 (same identical query, already pointed at from there) rather than duplicating it.
- **RKH-11** — `knowledge/mtn-sa-cdn-log-correlation-methodology.md`: harvest the submodule's raw CDN-log field reference and MTN network-team escalation criteria from `LEGEND.md`'s "CDN log fields"
  section and `docs/STATUS.md`, cross-linked to (not duplicating) `knowledge/ctap-smvod-pipeline.md`'s existing content-UUID-matching algorithm pitfalls.

**Batch 5 (root `investigations/` — reclassified out of the infra-folder exclusion, same treatment as `aws-access-cli`; the root case-index folder itself, not a submodule):**
- **RKH-12** — `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md`: harvest the four 2026-07-24 DRM/trace-analysis docs (`docs/20260724-mtn-sa-onetv1-4032-vod-drm-license-flow-analysis.md`,
  `docs/20260724-mtn-vs-timplay-vod-flow-comparison.md`, `docs/20260724-timplay-mileto-vod-ctap-sm-vod-mdrm-trace-analysis.md`, `docs/20260724-timplay-tenant-configuration-ltv-playback-analysis.md`)
  that are missing from `investigations/README.md`'s own case-index table — a stale-index gap flagged during spec-authoring, not fixed at the source (read-only).
- **RKH-13** — `knowledge/mtn-tenant-identifiers-and-code-flow.md`: harvest `docs/ITZUu4aBswL.md` + `docs/ITZUu4aBswL_code_flow.md` (flagged in the case index as "source of truth for MTN tenant IDs";
  full HAR→code-flow trace covering login, VOD playback, mDRM Widevine license, Kinesis analytics), with a forward-note that `docs/plan/tenant-registry/` (this repo's own not-yet-implemented story)
  should consult this file once its resolver work begins.
- **RKH-14** — port `github_copilot/knowledge/{ctap-shared-content-default-limit,mpd-shaka-restrictions-analysis,recommendation-engine-thinkanalytics}.md` into `ih-trace-lab/knowledge/` as-is (3
  files, one task, same porting pattern as RKH-2), cross-linked to RKH-12 where underlying case docs overlap.
- **RKH-15** — `knowledge/mtn-lightstep-identity-and-session-investigation-methodology.md`: distill the reusable facts/methodology (not the full executable playbook prompts) from
  `instructions/{lightstep-mcp-tool-notes,client-identity-investigation,device-flow-analysis,oauth-session-guard-interleave,drm-cross-region-investigation}.md` — MCP query syntax hard rules,
  householdId→clientId resolution steps, device/CTAP flow tracing, OAuth⇄session-guard interleave rules, EU⇄US DRM trace-correlation technique.
- **RKH-16** — `knowledge/mtn-har-kinesis-and-manifest-analysis-methodology.md`: distill the reusable facts/methodology from
  `instructions/{har-playback-flow-analysis,kinesis-stream-analysis,mpd-analysis,device-ua-playsession-analysis}.md` — HAR playback-flow reconstruction approach, Kinesis `PutRecords` decode/flatten
  rules, MPD/DASH analysis rules (cross-linked to RKH-14's ported `mpd-shaka-restrictions-analysis.md` instead of duplicating), device/UA CSV analysis approach.

**Batch 6 (`sre`, reclassified out of the infra-folder exclusion — its `data/`/`reports/` raw exports and dated skill-run outputs stay excluded, but its `docs/*.md` knowledge does not):**
- **RKH-17** — `knowledge/sre-jira-project-reference.md`: harvest `sre/docs/{sre-jira-knowledge,SRE_Quarterly_Jira_Query_Prompt}.md` — Jira project SRE's daily-operational-story/Q2-epic-driven-work
  structure, key custom-field IDs, days-based story-points convention, Initiative→Epic→Story hierarchy plus generalized quarterly JQL templates, and the `/sre*` skills reference table; no root
  `knowledge/*.md` currently references this folder, so it is a single harvest-only task.

## Definition of done

- `knowledge/vod-asset-field-mapping.md` states the four-ID-family navigation table and the ADI→API/Mongo field correspondences clearly enough to answer "which OpsHub/HAR/Lightstep/Mongo field does
  ADI field X map to" without opening the submodule.
- `knowledge/vod-asset-ingestion-pipeline.md` and `knowledge/ctap-smvod-pipeline.md` exist in `ih-trace-lab`, matching the source distillations but with the MongoDB-gap claim corrected and a
  cross-link to `knowledge/vod-asset-field-mapping.md` (no duplicated field tables between the three files — link, don't repeat).
- `knowledge/vod-asset-ingestion-pipeline.md` carries one clearly-flagged "Related, not yet harvested" pointer to `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`.
- `knowledge/mtn-sa-lightstep-span-attributes-by-service.md`, `knowledge/mtn-sa-lightstep-query-templates.md`, and `knowledge/applause-csv-household-id-gotchas.md` exist, each preserving its source's
  findings without an issue-specific framing baked into the file's stated purpose.
- `knowledge/mtn-sa-service-correlation-maps.md` exists and its `session-guard` "no edges" gap is cross-linked (not duplicated) to `knowledge/mtn-sa-lightstep-span-attributes-by-service.md`;
  `knowledge/ctap-smvod-pipeline.md` gains a cross-link to the same file plus `knowledge/mtn-sa-lightstep-query-templates.md` for shared `ctap`/`sm-vod` detail.
- `knowledge/mtn-sa-playback-outcome-and-error-taxonomy.md` and `knowledge/mtn-sa-cdn-log-correlation-methodology.md` exist, each preserving `ctap-smvod-session-report`'s own findings
  (playback-outcome taxonomy, lifecycle/error schema, missing-row methodology, CDN log field semantics, MTN escalation criteria) without duplicating
  `knowledge/mtn-adoption-playback-outcome-classification-gap.md`'s (RKH-8) classification-gap analysis or `knowledge/ctap-smvod-pipeline.md`'s (RKH-2/RKH-6) content-UUID-matching algorithm pitfalls —
  link to both instead.
- `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md` exists, preserves the four 2026-07-24 docs' cross-tenant DRM/session findings (MTN SA `iye9omdf` vs. TIM Play/mileto `iljyxcc3`), and
  flags the source folder's stale case-index gap without editing the read-only source.
- `knowledge/mtn-tenant-identifiers-and-code-flow.md` exists, preserves `ITZUu4aBswL.md`/`_code_flow.md`'s tenant-ID facts and full HAR→code-flow trace, and forward-notes `docs/plan/tenant-registry/`
  as the eventual consumer.
- `knowledge/ctap-shared-content-default-limit.md`, `knowledge/mpd-shaka-restrictions-analysis.md`, and `knowledge/recommendation-engine-thinkanalytics.md` exist in `ih-trace-lab`, ported as-is,
  cross-linked to RKH-12 where their underlying case docs overlap.
- `knowledge/mtn-lightstep-identity-and-session-investigation-methodology.md` and `knowledge/mtn-har-kinesis-and-manifest-analysis-methodology.md` exist, each distilling their five/four source
  playbooks' reusable facts and methodology (not the full executable prompt text) without duplicating each other or RKH-14's ported `mpd-shaka-restrictions-analysis.md`.

## Folder backlog

Tracks every `github_copilot/*` candidate folder this story could eventually cover. `status` is the only field that changes as the story progresses: `not started` → `spec'd` (RKH-N task(s) exist in
`tasks.md`/`stories.md` but not yet executed) → `harvested` (task(s) executed, checkbox ticked); a folder can also land on `excluded (no reusable knowledge)` if review finds nothing worth harvesting.
Infra folders (`config`, `copilot`, `knowledge`, `plan`, `scratch`, `scripts`) are deliberately excluded from this table — they hold no project-specific investigation knowledge of their own and are
never spec'd. `aws-access-cli`, the root `investigations/` folder, and `sre` were all reclassified out of this exclusion (see their rows below): `aws-access-cli`'s automation/CLI code stays out of
scope, but its dated `docs/2026-09-*.md` investigation write-ups do not; `investigations/`'s `data/`, `har/`, `scripts/`, `athenaCSV/`, `spancsv/`, and `xmls_or_mpd/` stay out of scope, but its
`docs/` case write-ups and `instructions/` playbooks do not; `sre`'s `data/*.csv` (raw Jira exports) and `reports/*.md` (dated generated report outputs) stay out of scope, but its `docs/*.md` (Jira
project structure, custom fields, quarterly query templates) does not. `astro-events-household-report`, `mtn-zm-session-device-investigation`, `mtn-network-traffic`, `oasis-athena-mcp`,
`shaka-6001-sa-error-analysis`, `vod-playback-timing-probe`, and `smarttv-mtntv` were reviewed and found to hold no reusable knowledge beyond tool/usage docs or their own internal plan stories — see
their rows below for the per-folder reasoning.

| Folder | Status | Notes |
| --- | --- | --- |
| `vod-asset-ingestion-mapping` | spec'd (RKH-1, RKH-2 not yet executed) | first batch |
| `applauseInvestigation` | spec'd (RKH-3, RKH-4, RKH-5, RKH-6, RKH-7 not yet executed) | 3 own knowledge files (span attributes, query templates, CSV/household-ID gotchas) split one-per-task,
RKH-6 porting/cross-linking `mtn-sa-service-correlation-maps.md` and `ctap-smvod-pipeline.md`, and RKH-7 covering the `investigations/` subfolder (Athena bridge keys + HAR Device ID recovery gotcha)
missed by the first spec pass |
| `ctap-smvod-session-report` | spec'd (RKH-10, RKH-11 not yet executed) | has `docs/`, `BLUEPRINT.md`, `LEGEND.md`, query catalog — the root `knowledge/ctap-smvod-pipeline.md` overlap flagged
below was already fully claimed by RKH-2/RKH-6 (session/CDN-matching-algorithm facts) and `aws-access-cli`'s RKH-8 already reserves a pointer to this folder's identical `playback_outcome`
classification-gap query, so RKH-10/RKH-11 are scoped to the two remaining un-claimed knowledge domains: playback-outcome/error taxonomy and raw CDN log field semantics |
| `astro-events-household-report` | excluded (no reusable knowledge) | reviewed `QUERY_CATALOG.md`/`README.md`/`queries/*.md` — confirmed no usable distillable knowledge beyond what the
`query-catalog` story already covers; not spec'd |
| `mtn-zm-session-device-investigation` | excluded (no reusable knowledge) | reviewed `README.md` + `docs/multi-investigation-config/{prompt,tasks,stories}.md` — its own internal plan story, not
investigation findings; confirmed no usable knowledge; not spec'd |
| `mtn-network-traffic` | excluded (no reusable knowledge) | reviewed `README.md`, `docs/usage.md`, `output/run1.md` — thin usage doc + one generated output run; confirmed no usable knowledge;
not spec'd |
| `oasis-athena-mcp` | excluded (no reusable knowledge) | reviewed `README.md`, `CONTRIBUTING.md`, `docs/{table-ddl-knowledge-guide,mcp-server-setup}.md`, `docs/plans/athena-mcp-server/*.md` —
tool/setup docs and its own internal plan story, not reusable investigation knowledge; confirmed no usable knowledge; not spec'd |
| `shaka-6001-sa-error-analysis` | excluded (no reusable knowledge) | thin folder (`scripts/`, `output/`, one `session-info.md`) — confirmed no usable knowledge; not spec'd |
| `vod-playback-timing-probe` | excluded (no reusable knowledge) | reviewed `README.md`, `QUICKSTART.md`, `AGENTS.md`, `docs/{usage,contributing}.md`,
`docs/plans/segment-timeline-and-reporting-gaps.md` — tool/usage docs and its own internal plan story, not reusable investigation knowledge; confirmed no usable knowledge; not spec'd |
| `smarttv-mtntv` | excluded (no reusable knowledge) | confirmed: only `scripts/` + `downloaded/`, no `docs/`/`README` at all; treated like an infra folder; not spec'd |
| `aws-access-cli` | spec'd (RKH-8, RKH-9 not yet executed) | initially listed as excluded infra below, then reclassified: its `docs/2026-09-*.md` holds genuine dated investigation findings (adoption
`playback_outcome` classification gap) distinct from its Athena-automation-CLI role; `docs/database-abstraction/` and `docs/plans/` are its own internal refactor-story docs, not reusable domain
knowledge, and stay out of scope |
| `investigations` (root, not a submodule) | spec'd (RKH-12, RKH-13, RKH-14, RKH-15, RKH-16 not yet executed) | initially listed as excluded infra, then reclassified: `docs/` (case write-ups, several
already promoted to root `knowledge/*.md`) and `instructions/` (9 executable Copilot playbook-prompts, none yet promoted) both hold genuine reusable content; `data/`, `har/`, `scripts/`, `athenaCSV/`,
`spancsv/`, `xmls_or_mpd/` stay out of scope (raw/gitignored artifacts and analysis scripts, not knowledge docs) |
| `sre` | spec'd (RKH-17 not yet executed) | initially listed as excluded infra, then reclassified: `docs/sre-jira-knowledge.md` + `docs/SRE_Quarterly_Jira_Query_Prompt.md` hold genuine reusable
project-structure/field-ID/JQL-template knowledge, not referenced by any existing root `knowledge/*.md` (single harvest-only task, no port/correct half); `data/*.csv` (raw Jira exports) and
`reports/*.md` (dated generated report outputs, one per skill run) stay out of scope |

## Adding a new folder (spec-authoring mode)

**Input:** `SOURCE_FOLDER` — one folder name from the backlog table above, named by whoever starts the session (e.g. "harvest `applauseInvestigation` next"). Refuse if it's not in the table, or is
already `harvested`/`spec'd`, or is one of the excluded infra folders — ask instead of guessing.

1. **Confirm classification** — open `SOURCE_FOLDER` and check it actually has its own `docs/`/`README`/knowledge-bearing files (not just `scripts/`/`output/`). If it turns out to be infra-only, say
   so, update its backlog row to note the exclusion, commit that one-line correction, and stop — do not spec a task for it.
2. **Find linkage** — `grep`/scan `/Users/abhadra/github_copilot/knowledge/*.md` for any file that already references `SOURCE_FOLDER` (by name, by shared span names, or by shared field names). List
   what's found; if nothing references it, the batch is a single task (harvest-only, no port/correct half).
3. **Inventory `SOURCE_FOLDER`'s own docs** — read its `README`/`STATUS`/`docs/*.md`/case-index equivalents. Separate: (a) content genuinely reusable here (field/property mappings, ID rules, gotchas,
   query templates, span-attribute references) → goes in the harvest task; (b) content that actually belongs to a *different* backlog folder's future task → leave one labeled "Related, not yet
   harvested" pointer sentence, do not summarize or copy it.
4. **Decide the split** — default 2 tasks (own field-mapping/knowledge doc + port/correct any root distillation found in step 2); collapse to 1 if step 2 found nothing; if it looks like more than 2
   are needed, stop and ask before proceeding.
5. **Append, don't rewrite** — add new `RKH-N`(+1) rows to `tasks.md` (same `Owner | Model | Review | SHA` row shape as RKH-1/RKH-2) and new sections to `stories.md` (same
   grounding/files-to-change/what-to-implement/tests/commit shape as the RKH-1 section). Update this file's "Task overview" section to add the new batch, and flip `SOURCE_FOLDER`'s backlog row to
   `spec'd`. Do not edit RKH-1/RKH-2's existing content.
6. **Reflow, commit, verify** — run `scripts/dev/reflow_md.py` on every touched file, stage, commit (message: `docs(plan): spec RKH-N/RKH-N+1 for <SOURCE_FOLDER>`), then run `git show
   HEAD:docs/plan/reference-knowledge-harvest/tasks.md` (and `stories.md`) to confirm the new content actually landed at `HEAD` — do not trust `git status`/`git diff --cached` alone. Stop; do not
   execute the new task in this same session.

## Perspectives not covered

- RKH-1/RKH-2 do not attempt to harvest or even summarize any other `github_copilot/*` project — each future folder gets its own `RKH-N` task, added to this same story when that folder is next up,
  never bundled with another folder's task.
