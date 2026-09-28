# Target folder/file structure

Single source of truth for the end-state layout this pair of stories (`project-taxonomy` + `functional-code-taxonomy`) builds toward. Every task in either story's `stories.md` that touches file/folder
layout points here instead of re-describing the tree inline — if this file and a task spec ever disagree, this file wins (update the task spec, not this file, unless a new discussion round explicitly
changes the target layout — see the Invariant at the bottom).

Legend: `[PT-N]` / `[FCT-N]` = the task that creates or last defines that node. Nothing below exists yet — both stories are plan-only as of this pass.

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
│   │   ├── queries/
│   │   │   └── QUERY_CATALOG.md
│   │   ├── scripts/                          [PT-2, Rule A] thin, direct child — no inner `investigations/` wrap;
│   │   │                                      imports src/lib/* (no local athena_runner/.venv/pytest.ini duplicated
│   │   │                                      per project — see mtn-zm's 4th Athena executor as the cautionary example)
│   │   └── tests/
│   ├── <case-id>/                            [PT-2, revised Rule B] standalone case, no campaign yet — same
│   │   │                                      docs/queries/scripts/tests skeleton as above, minus the campaign layer;
│   │   │                                      promoted (renamed) to <campaign-slug>/<case-id>/ once a 2nd related
│   │   │                                      case appears — raw inputs live in root data/<case-id>/, not here
│   │   └── docs/  queries/  scripts/  tests/
│   └── <continuous-investigation-slug>/      e.g. `ctap-smvod` — real submodule (own remote, own git root)
│       ├── .github/copilot-instructions.md   loads independently — own `git rev-parse --show-toplevel` (verified)
│       ├── docs/  queries/  scripts/
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
└── knowledge/                                  [PT-7] tool-first, cross-campaign, OPTIONAL — the opposite axis from
    │                                            data/ and investigations/*/docs/ (case-first, always written)
    ├── lightstep/                             e.g. "span attribute X is unreliable for platform detection" — true
    ├── athena/                                 regardless of which case discovered it; promote only case-independent
    └── har/                                    mechanism facts (see the promotion test in the paragraph below)
```

`knowledge/<tool>/` vs. `investigations/*/docs/`: `docs/` is the mandatory per-case deliverable — every investigation
produces one, it is what gets shared outside this project to explain what happened, and it stays tied to that case's
ticket/household/device IDs forever. `knowledge/` is an optional, opportunistic side-effect — most cases produce
nothing for it. Promotion test: would this fact still be true and useful on a *different* ticket, with different
household/device IDs? If yes → `knowledge/<tool>/`. If it only makes sense with this ticket's specifics → it stays in
`docs/`. Never write to `knowledge/` just to "use" the folder — a small, high-signal `knowledge/` is the point.

## Invariant

If a future discussion round changes the target layout, update this file in the same turn as any resulting `tasks.md`/`stories.md` edits in either story — this file and both stories' task specs must
never describe two different end states.
