# Query catalog — prompt

> A durable, deduplicated, token-efficient catalog of Athena and Lightstep queries — templates first, script promotion only when reuse needs post-processing logic.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot` has three `QUERY_CATALOG.md` files (`applauseInvestigation`, `ctap-smvod-session-report`, `astro-events-household-report`) recording every Athena query written during
past investigations, plus a `knowledge/lightstep-query-templates.md` doing the equivalent for Lightstep TQL. They show two failure modes worth not repeating: `ctap-smvod-session-report`'s catalog grew
into a single 113KB file (unreadable, unmergeable); `applauseInvestigation`'s catalog re-types the *same* query shape verbatim across two issues (7231547, 7232657) because each entry was saved with
literal IDs baked in rather than as a reusable template. Every one of those queries cost real tokens to derive (table discovery, join-key reasoning, trial-and-error against real schema) — that
investment should never have to be re-paid.

`ctap-smvod-session-report/queries/` is also this story's best piece of prior art for the *fix*, not just an example of the mega-catalog problem: alongside its own outgrown `QUERY_CATALOG.md`, it
already promotes individual finalized/topic-scoped queries into their own files — `athena_session_outcome.md` (the production `playback_outcome` query, finalized), `adoption.md` (adoption-report query
set), `edge_4032_playback_failure.md` (a drafted-but-not-yet-run investigation thread) — exactly the "index for scanning, standalone file per shape" split this story's `queries/athena/` design is
built around. Treat this folder as the holy-grail reference for what a mature Athena query set looks like in this domain: QC-2's harvest must read these promoted files too, not just the mega-catalog,
and must carry forward each file's own run-status (confirmed-run vs. drafted-not-yet-run) rather than assuming everything harvested is production-verified.

This story gives `ih-trace-lab` a catalog that fixes both problems at once: a cheap-to-scan `index.md` per data source (not a monolith) for the "does this already exist" check, and parameterized
templates saved from the first write (not promoted after N reuses — usage can't be reliably counted anyway, since query execution happens outside this assistant, run manually against
Athena/Lightstep). Script promotion is reserved for a different, directly observable signal: reuse that needs real post-processing logic (CSV joins, pivoting, report generation), not just parameter
substitution — exactly what `applauseInvestigation/scripts/analyze_athena_playback.py` and `ctap-smvod-session-report/scripts/merge_session_outcome.py` already are.

## Scope guard

**In scope:** `queries/README.md` (folder purpose + rules), `queries/athena/` and `queries/lightstep/` each with their own `index.md` + one template file per distinct query shape, a one-time static
harvest of the 4 reference catalog files named above plus `ctap-smvod-session-report/queries/`'s 3 promoted finalized-query files (`athena_session_outcome.md`, `adoption.md`,
`edge_4032_playback_failure.md`) (parsing already-committed markdown — no live Athena/Lightstep queries run), a `knowledge/` DDL-cache convention doc plus ported (not executed) tooling scripts, a
short `docs/guides/query-catalog.md` protocol doc, and an `AGENTS.md` pointer line.

**Out of scope:** running any live Athena or Lightstep MCP query to populate a fresh `knowledge/*-tables.md` DDL cache — that requires the tenant/profile resolution `docs/plan/tenant-registry/` is
still building (TR-1..6 all open); this story only ports the reusable *scripts* for that job, it does not run them. No changes to `/Users/abhadra/github_copilot` (read-only reference). No change to
how queries are actually executed (still manual, by the user, against Athena/Lightstep) — this story only organizes what gets saved before/after that. `ctap-smvod-session-report/queries/ exploration/`
and `stories/` (DDL-discovery narrative, not queries meant for reuse) and `backups/` (superseded pre-`APP_KEEPALIVE` versions) stay out of scope — QC-2 harvests query shapes, not
narrative/DDL-discovery history.

## Session-start load hints

- `/Users/abhadra/github_copilot/applauseInvestigation/investigations/queries/QUERY_CATALOG.md`, `/Users/abhadra/github_copilot/ctap-smvod-session-report/queries/QUERY_CATALOG.md`,
  `/Users/abhadra/github_copilot/astro-events-household-report/QUERY_CATALOG.md` — the three Athena mega-catalogs being harvested (read-only source, do not edit).
- `/Users/abhadra/github_copilot/ctap-smvod-session-report/queries/{athena_session_outcome.md,adoption.md,edge_4032_playback_failure.md}` — this folder's own promoted, topic-scoped finalized queries
  (the "holy grail" exemplar of what this story's per-shape template files should look like) — harvest these too, not just its `QUERY_CATALOG.md` (read-only source, do not edit).
- `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md` — the Lightstep catalog being harvested (read-only source, do not edit).
- `/Users/abhadra/github_copilot/oasis-athena-mcp/docs/table-ddl-knowledge-guide.md` + `scripts/discover_athena_tables.py` + `scripts/run_table_ddl_export.py` +
  `/Users/abhadra/github_copilot/scripts/update_athena_table_ddl_knowledge.py` — the DDL-cache tooling being ported (read, do not edit the originals).
- `docs/plan/tenant-registry/prompt.md` — the prerequisite this story's DDL-cache task explicitly defers to; read its "Why this story exists" to understand why a live Athena/Lightstep call cannot
  happen yet.
- `scratch/SCRATCH.md` — the existing convergence-rule precedent this story's script-promotion trigger is modeled on (design POC repeats vs. plumbing repeats); read before writing QC-5.

## Task overview

- **QC-1** — `queries/README.md`: folder purpose, `athena/`/`lightstep/` layout, and the core rules (check `index.md` first, template-first with placeholders, when to promote to a script).
- **QC-2** — `queries/athena/`: harvest script parsing the 3 reference `QUERY_CATALOG.md` mega-catalogs plus `ctap-smvod-session-report/queries/`'s 3 promoted finalized-query files
  (`athena_session_outcome.md`, `adoption.md`, `edge_4032_playback_failure.md`) into deduplicated `queries/athena/<slug>.sql` templates + `queries/athena/index.md` rows, each row carrying a run-status
  (confirmed-run vs. drafted-not-yet-run).
- **QC-3** — `queries/lightstep/`: harvest script parsing `lightstep-query-templates.md` into `queries/lightstep/<slug>.md` template files (native TQL, already parameterized) + `index.md` rows.
- **QC-4** — `knowledge/`: port (not run) the DDL-cache tooling scripts + a `knowledge/README.md` explaining the convention and its tenant-registry prerequisite.
- **QC-5** — `docs/guides/query-catalog.md` protocol doc + `AGENTS.md` pointer line.
- **QC-6** — Tests for both harvest scripts (QC-2, QC-3): dedup-by-shape happy path, malformed/no-SQL-block input edge case.

## Definition of done

- `queries/README.md` states the folder's purpose and rules clearly enough that a new session can follow them without re-deriving this design.
- `queries/athena/index.md` and `queries/lightstep/index.md` each list every distinct query shape harvested from the reference catalogs (including `ctap-smvod-session-report/queries/`'s promoted
  finalized-query files, not just its mega-catalog), with no two rows describing the same underlying question with only literal IDs differing, and each Athena row carries a run-status (confirmed-run
  vs. drafted-not-yet-run).
- Every harvested query is a parameterized template file (`{{placeholder}}` style), not a literal one-off.
- `knowledge/README.md` documents the DDL-cache convention and names its tenant-registry prerequisite; the ported scripts are present but not executed against any live Athena database.
- `docs/guides/query-catalog.md` states the "check index → check knowledge DDL cache → write template → promote to script only if post-processing needed" workflow; `AGENTS.md` gained exactly one
  pointer line to it.
- Harvest script tests green.

## Perspectives not covered

- Matisse queries/traces are not covered by this story — only Athena and Lightstep, the two sources actually in use today per this session's scope. A third source folder (e.g. `queries/matisse/`)
  should be added the same way, once it's actually needed, not pre-created speculatively.
- This story does not solve near-duplicate detection *within* the harvest itself beyond table+join-key shape matching — a query that's genuinely a different shape but happens to look similar in prose
  could still land as two entries; that's an acceptable false-negative for a first pass, not something this story's harvest script is required to catch perfectly.
