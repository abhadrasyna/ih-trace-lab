# Target folder/file structure

Single source of truth for the end-state layout the three stories that touch file/folder layout (`project-taxonomy`, `functional-code-taxonomy`, `query-catalog`) build toward. Every task in any of
their `stories.md` that touches file/folder layout points here instead of re-describing the tree inline — if this file and a task spec ever disagree, this file wins (update the task spec, not this
file, unless a new discussion round explicitly changes the target layout — see the Invariant at the bottom).

Legend: `[PT-N]` / `[FCT-N]` / `[QC-N]` = the task that creates or last defines that node. Nothing below exists yet — all three stories are plan-only as of this pass.

```
ih-trace-lab/
├── AGENTS.md                                 [PT-5, FCT-4] pointers to the two guides below
├── CONTEXT.md                                tracks story status in "What Exists"
├── pyproject.toml                            testpaths/coverage/lint list src/, investigations/, experiments/ — not src/ alone
│
├── config/
│   └── data_paths.yaml                       [PT-7] single source of truth for data_root/knowledge_root/investigations_root
│                                              path templates — src/lib/paths reads this, never hardcodes shape
│
├── docs/
│   ├── guides/
│   │   ├── project-taxonomy.md               [PT-1/2/3/6] categories, skeletons, Rule A/B, cron-cutover, script-level
│   │   │                                      prior-art checklist
│   │   └── functional-code-taxonomy.md       [FCT-1/2/3] module map, shared-vs-specific test, category→module table
│   └── plan/
│       ├── project-taxonomy/
│       │   └── structure.md                 this file
│       └── functional-code-taxonomy/
│
├── src/
│   ├── lib/                                   shared, installable, tested — the ONLY place domain-mechanism code lives
│   │   ├── auth/                             deferred — no proven 2nd duplicate yet
│   │   ├── athena/
│   │   │   └── protocols.py                  [FCT-2] AthenaClient Protocol — replaces 3 duplicated executors
│   │   │                                      (oasis-athena-mcp, ctap-smvod-session-report, aws-access-cli)
│   │   ├── csv_io/                           deferred
│   │   ├── report_render/
│   │   │   └── protocols.py                  [FCT-2] ReportRenderer Protocol — replaces 8+ duplicated CSV/report writers
│   │   ├── har/
│   │   │   └── protocols.py                  [FCT-2] HarEntryLoader Protocol — replaces the 4x-duplicated HAR-entries
│   │   │                                      loader (applauseInvestigation, vod-playback-timing-probe x2); seeded from
│   │   │                                      vod-asset-ingestion-mapping's scripts/lib/har_parser.py
│   │   ├── curl_to_python/                   deferred
│   │   └── paths/
│   │       └── protocols.py                  [FCT-7] PathResolver Protocol — reads config/data_paths.yaml, exposes
│   │                                          resolve_input_dir/resolve_knowledge_dir/resolve_investigation_dir;
│   │                                          scripts never hardcode data/knowledge/investigations shape
│   ├── tools/                                 category: tool — reusable software with its own interface/protocol,
│   │   │                                      actively maintained/enhanced across many callers (not a case-tracking
│   │   │                                      folder, so no investigations/)
│   │   └── <tool-slug>/                      e.g. an oasis-athena-mcp equivalent, once ported
│   │       ├── src/                          [PT-2] imports src/lib/* where applicable
│   │       ├── tests/                        [PT-2]
│   │       └── README.md                     [PT-2] its own — distinct from the reusable src/lib/* Protocol docs
│   └── pipelines/                             category: pipeline
│       └── <pipeline-slug>/                  e.g. an aws-access-cli equivalent, once ported (see PT-6 cron-cutover)
│           ├── scripts/                      thin — imports src/lib/*
│           ├── tests/
│           └── README.md                     documents schedule/trigger and operator-facing behavior
│
├── data/                                       [PT-7] raw tool inputs — root .gitignore'd wholesale (disposable,
│   │                                            never committed); shape driven by config/data_paths.yaml, not hardcoded
│   ├── <campaign-slug>/                       campaign case — e.g. `applause`, `mtn-zm-device`
│   │   └── <case-id>/
│   │       ├── har/                          present only if this tool was actually used and saved — a HAR-only
│   │       ├── lightstep/                    case is normal, not a gap; manual/interactive Lightstep or Athena
│   │       └── athena/                       queries that produced nothing worth saving leave no folder here —
│   │                                          see the case doc's "Inputs used" block for the methodology record
│   └── <case-id>/                            [PT-2, revised Rule B] standalone case, no campaign yet — no `misc/`
│                                              wrapper; promoted (renamed) to <campaign-slug>/<case-id>/ above once
│                                              a 2nd related case appears
│       ├── har/  lightstep/  athena/
│
├── investigations/                            category: investigation (bounded case or recurring campaign — no
│   │                                            separate "continuous investigation" category; a submodule buys
│   │                                            nothing here, see the 2026-09-28 discussion round's conclusion)
│   ├── <campaign-slug>/                      [PT-2, Rule B] e.g. `applause` (was applauseInvestigation), `mtn-zm-device`
│   │   │                                      (was mtn-zm-session-device-investigation), `ctap-smvod` (was a
│   │   │                                      separate-remote submodule — plain folder now, no benefit found from
│   │   │                                      the submodule boundary), `vod-asset-ingestion` (was
│   │   │                                      vod-asset-ingestion-mapping — recategorized from `experiments/` to
│   │   │                                      here by `reference-code-gap-migration` GAP-1, 2026-09-30: its own
│   │   │                                      README calls it "a continuous data-gathering exercise", i.e. a
│   │   │                                      recurring campaign, not a throwaway probe) — one slug per
│   │   │                                      campaign/relationship, not per case
│   │   ├── docs/
│   │   │   ├── <case-id>-<topic>.md          flat, ID-prefixed — no per-case subfolder [PT-2, Rule B]; mandatory
│   │   │   │                                  deliverable per bounded case (shared outside this project) — every
│   │   │   │                                  case gets one, unlike knowledge/ below
│   │   │   ├── <case-id>-executive-summary.md
│   │   │   ├── <date>-<topic>.md             for a campaign running a recurring/no-close-event pipeline (was
│   │   │   │                                  "continuous investigation"): dated sections replace case-id sections
│   │   │   │                                  — e.g. `2026-08-01-position-report.md`
│   │   │   └── archive/                      closed *bounded* cases move here (case-level close-out); a recurring
│   │   │                                      campaign has no case-level close-out — see RETENTION.md below
│   │   ├── scripts/                          [PT-2, Rule A] thin, direct child — no inner `investigations/` wrap;
│   │   │                                      imports src/lib/* (no local athena_runner/.venv/pytest.ini duplicated
│   │   │                                      per project — see mtn-zm's 4th Athena executor as the cautionary example)
│   │   ├── tests/                            no `queries/` here — see root `queries/` below; Athena/Lightstep query
│   │   │                                      templates are cross-campaign facts (same axis as root `knowledge/`),
│   │   │                                      not per-case ones, so they never live under `investigations/*`
│   │   ├── data/                             OPTIONAL [PT-7] — present only if this campaign runs a recurring
│   │   │   │                                  per-date pipeline (was the continuous-investigation-only local
│   │   │   │                                  `data/`); absent entirely for a normal bounded-case campaign, which
│   │   │   │                                  uses root `data/<campaign-slug>/<case-id>/` instead. Split by
│   │   │   │                                  *source/tool provenance*, not input-vs-output, because step N's
│   │   │   │                                  output is legitimately step N+1's input in a linear chain
│   │   │   ├── lightstep/                    true Step 1 manual exports (no live API) — ISO-prefix filenames,
│   │   │   │                                  tool name dropped (folder already carries it): e.g.
│   │   │   │                                  `2026-08-01_ctap.csv`, `2026-08-01_smvod.csv`, `2026-08-01_smvod_ts.csv`
│   │   │   └── athena/                       Athena pulls made by this pipeline's own earlier steps, re-read as
│   │   │                                      a later step's input — e.g. `2026-08-01_session.csv`,
│   │   │                                      `2026-08-01_debug_states.csv`
│   │   ├── output/                           OPTIONAL [PT-7] — present only alongside `data/` above; post-merge
│   │   │                                      deliverables only, same ISO-prefix filename convention — e.g.
│   │   │                                      `2026-08-01_setupsession_with_outcome.csv`,
│   │   │                                      `2026-08-01_position_report.csv`; ranges as
│   │   │                                      `<start>_<end>_<artifact>.csv` (ticket tag trailing, never infix);
│   │   │                                      cumulative rollups (date lives as a row, not the filename) keep a
│   │   │                                      `_rollup`/`_all_dates` marker instead of a date — see PT-7's
│   │   │                                      filename-convention point for the full rule
│   │   └── RETENTION.md                      OPTIONAL, one line — e.g. "rolling, no close-out; see PT-7 close-out
│   │                                          policy exception" — only present if this campaign never closes (has
│   │                                          `data/`+`output/` above); a normal bounded-case campaign has no such
│   │                                          file and follows the default close-out (docs written → raw data
│   │                                          deleted)
│   └── <case-id>/                            [PT-2, revised Rule B] standalone case, no campaign yet — same
│       │                                      docs/scripts/tests skeleton as above (no `queries/` — see root
│       │                                      `queries/` below), minus the campaign layer; promoted (renamed) to
│       │                                      <campaign-slug>/<case-id>/ once a 2nd related case appears — raw
│       │                                      inputs live in root data/<case-id>/, not here
│       └── docs/  scripts/  tests/
│
├── experiments/                                category: experiment — only created once promoted from scratch/
│   └── <experiment-slug>/                    e.g. `vod-playback-timing-probe`-style (NOTE: `reference-code-gap-migration`'s
│                                              2026-09-30 audit suggests this project reads as a **tool** — reusable
│                                              CLI/package, not a throwaway probe — an unresolved tension with this
│                                              example, flagged for a future project-taxonomy session, not corrected
│                                              here; see that story's `spec.md` §1). `vod-asset-ingestion-mapping` was
│                                              removed from this example — see `investigations/` above.
│
├── scratch/                                    every experiment starts here (existing convergence rule, unchanged)
│
├── scripts/dev/
│   ├── check_project_taxonomy.py             [PT-4] flags unclassified top-level dirs against the taxonomy
│   ├── generate_scripts_registry.py          existing (scratch-script-registry) — scratch/scripts only
│   └── generate_code_registry.py             [FCT-6] extends the registry to investigations/*/scripts,
│                                               experiments/*/scripts, src/pipelines, src/tools — the mandatory
│                                               pre-write duplicate-check now covers every new script, not just
│                                               scratch probes
│
├── queries/                                    [QC-1..3] cross-campaign, deduplicated Athena/Lightstep query
│   │                                            catalog — same axis as knowledge/ below, not investigations/*;
│   │                                            replaces the old per-campaign investigations/*/queries/QUERY_CATALOG.md
│   │                                            pattern, which let the same query shape get re-typed per campaign
│   ├── athena/
│   │   ├── index.md                          [QC-2] one row per distinct query shape — check this before writing
│   │   │                                      any new Athena SQL
│   │   └── <slug>.sql                        [QC-2] parameterized template ({{placeholder}} params), never a
│   │                                          literal one-off; header comment: purpose/tables/params/source
│   └── lightstep/
│       ├── index.md                          [QC-3] same pattern, keyed on service/operation/attribute
│       └── <slug>.md                         [QC-3] native TQL block, already parameterized in source form
│
└── knowledge/                                  [PT-7] tool-first, cross-campaign, OPTIONAL — the opposite axis from
    │                                            data/ and investigations/*/docs/ (case-first, always written); one
    │                                            subfolder per tool keeps promoted findings grouped by provenance
    ├── lightstep/
    │   └── <topic>.md                        e.g. `span-attributes-by-service.md` — "span attribute X is unreliable
    │                                          for platform detection", regardless of which case found it
    ├── athena/
    │   └── <project>-<db>-tables.md          [QC-4] DDL cache, one file per Athena database — promote only
    │                                          case-independent mechanism facts (see the promotion test below)
    └── har/
        └── <topic>.md                        e.g. `csv-household-id-gotchas.md` — same convention, HAR side
```

`knowledge/<tool>/<topic>.md` vs. `investigations/*/docs/`: `docs/` is the mandatory per-case deliverable — every investigation produces one, it is what gets shared outside this project to explain
what happened, and it stays tied to that case's ticket/household/device IDs forever. `knowledge/` is an optional, opportunistic side-effect — most cases produce nothing for it. Promotion test: would
this fact still be true and useful on a *different* ticket, with different household/device IDs? If yes → `knowledge/<tool>/<topic>.md`. If it only makes sense with this ticket's specifics → it stays
in `docs/`. Never write to `knowledge/` just to "use" the folder — a small, high-signal `knowledge/` is the point.

## Invariant

If a future discussion round changes the target layout, update this file in the same turn as any resulting `tasks.md`/`stories.md` edits in any of the three stories — this file and all three stories'
task specs must never describe two different end states.

## 2026-09-30 correction (`reference-code-gap-migration` GAP-1)

`vod-asset-ingestion-mapping` moved from this file's `experiments/` worked example to `investigations/<campaign-slug>/` (slug `vod-asset-ingestion`) — see the `investigations/` tree above for the
one-line reason. `vod-playback-timing-probe` stays under `experiments/` here despite that same audit suggesting **tool** as its better fit; that tension is flagged, not resolved, pending a future
project-taxonomy session (PT-1 is not yet implemented, so no live doc drift resulted from either finding).
