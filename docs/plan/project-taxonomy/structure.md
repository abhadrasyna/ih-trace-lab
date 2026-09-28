# Target folder/file structure

Single source of truth for the end-state layout the three stories that touch file/folder layout (`project-taxonomy`, `functional-code-taxonomy`, `query-catalog`) build toward. Every task in any
of their `stories.md` that touches file/folder layout points here instead of re-describing the tree inline — if this file and a task spec ever disagree, this file wins (update the task spec, not
this file, unless a new discussion round explicitly changes the target layout — see the Invariant at the bottom).

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
│   ├── tools/                                 category: tool
│   │   └── <tool-slug>/
│   └── pipelines/                             category: pipeline
│       └── <pipeline-slug>/                  e.g. an aws-access-cli equivalent, once ported (see PT-6 cron-cutover)
│           ├── scripts/                      thin — imports src/lib/*
│           └── tests/
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
├── investigations/                            category: continuous + one-off investigation
│   ├── <campaign-slug>/                      [PT-2, Rule B] e.g. `applause` (was applauseInvestigation), `mtn-zm-device`
│   │   │                                      (was mtn-zm-session-device-investigation) — one slug per campaign/
│   │   │                                      relationship, not per case
│   │   ├── docs/
│   │   │   ├── <case-id>-<topic>.md          flat, ID-prefixed — no per-case subfolder [PT-2, Rule B]; mandatory
│   │   │   │                                  deliverable per case (shared outside this project) — every case gets
│   │   │   │                                  one, unlike knowledge/ below
│   │   │   ├── <case-id>-executive-summary.md
│   │   │   └── archive/                      closed cases move here (case-level close-out)
│   │   ├── scripts/                          [PT-2, Rule A] thin, direct child — no inner `investigations/` wrap;
│   │   │                                      imports src/lib/* (no local athena_runner/.venv/pytest.ini duplicated
│   │   │                                      per project — see mtn-zm's 4th Athena executor as the cautionary example)
│   │   └── tests/                            no `queries/` here — see root `queries/` below; Athena/Lightstep query
│   │                                          templates are cross-campaign facts (same axis as root `knowledge/`),
│   │                                          not per-case ones, so they never live under `investigations/*`
│   ├── <case-id>/                            [PT-2, revised Rule B] standalone case, no campaign yet — same
│   │   │                                      docs/scripts/tests skeleton as above (no `queries/` — see root
│   │   │                                      `queries/` below), minus the campaign layer; promoted (renamed) to
│   │   │                                      <campaign-slug>/<case-id>/ once a 2nd related case appears — raw
│   │   │                                      inputs live in root data/<case-id>/, not here
│   │   └── docs/  scripts/  tests/
│   └── <continuous-investigation-slug>/      e.g. `ctap-smvod` — real submodule (own remote, own git root)
│       ├── .github/copilot-instructions.md   loads independently — own `git rev-parse --show-toplevel` (verified)
│       ├── docs/  scripts/                   queries go in root `queries/` (below), not a local `queries/` — same
│       │                                      cross-campaign-facts reasoning as the campaign/case cases above
│       ├── data/                             [PT-7, revised 2026-09-28] LOCAL, not root `data/` — this is a
│       │   │                                  repeating per-date pipeline, not a campaign/case; split by
│       │   │                                  *source/tool provenance*, not input-vs-output, because step N's
│       │   │                                  output is legitimately step N+1's input in a linear chain
│       │   ├── lightstep/                    true Step 1 manual exports (no live API) — e.g. ctap_*, smvod_*,
│       │   │                                  smvod_ts_*, one set per date
│       │   └── athena/                       Athena pulls made by this pipeline's own earlier steps, re-read as
│       │                                      a later step's input — e.g. athena_session_*, debug_states_*
│       ├── output/                           post-merge deliverables only — e.g. setupsession_with_outcome_*,
│       │                                      position_report_*, mtn_escalation_*, cdn_correlation_*
│       ├── debug/                            scratch/sample only, gitignored, never a pipeline dependency
│       └── knowledge/                        LOCAL staging only — promote reusable bits to root knowledge/
│
├── experiments/                                category: experiment — only created once promoted from scratch/
│   └── <experiment-slug>/                    e.g. `vod-asset-ingestion-mapping`, `vod-playback-timing-probe`-style
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
    │                                            data/ and investigations/*/docs/ (case-first, always written); flat
    │                                            files, no per-tool subfolders — an open-ended tool set (a new tool
    │                                            is just a new filename prefix) stays a cheap-to-scan single directory
    ├── lightstep-<topic>.md                  e.g. `lightstep-span-attributes-by-service.md` — "span attribute X is
    │                                          unreliable for platform detection", regardless of which case found it
    ├── <project>-athena-<db>-tables.md       [QC-4] DDL cache, one file per Athena database — promote only
    │                                          case-independent mechanism facts (see the promotion test below)
    └── har-<topic>.md                        e.g. `har-csv-household-id-gotchas.md` — same convention, HAR side
```

`knowledge/<tool>-<topic>.md` vs. `investigations/*/docs/`: `docs/` is the mandatory per-case deliverable — every investigation
produces one, it is what gets shared outside this project to explain what happened, and it stays tied to that case's
ticket/household/device IDs forever. `knowledge/` is an optional, opportunistic side-effect — most cases produce
nothing for it. Promotion test: would this fact still be true and useful on a *different* ticket, with different
household/device IDs? If yes → `knowledge/<tool>-<topic>.md`. If it only makes sense with this ticket's specifics → it stays in
`docs/`. Never write to `knowledge/` just to "use" the folder — a small, high-signal `knowledge/` is the point.

## Invariant

If a future discussion round changes the target layout, update this file in the same turn as any resulting `tasks.md`/`stories.md` edits in any of the three stories — this file and all three
stories' task specs must never describe two different end states.
