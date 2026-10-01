# Knowledge cache conventions

This folder holds durable, reusable reference knowledge extracted from earlier investigations so future Athena and Lightstep work starts from cached schema and attribute facts instead of re-deriving
them from live systems each time.

## Athena DDL-cache convention

Use one file per Athena database, named `knowledge/<project>-athena-<database>-tables.md`.

Each file should combine two things:

1. A generated `## DDL reference` section, refreshed from exported Athena metadata.
2. A hand-written categorized table inventory explaining which tables are canonical, derived, scratch, deprecated, or otherwise notable.

That mirrors the 4-step workflow documented in the read-only reference guide `/Users/abhadra/github_copilot/oasis-athena-mcp/docs/table-ddl-knowledge-guide.md`:

1. Discover every table in the target database with `scripts/athena/discover_athena_tables.py`.
2. Filter that full list down to the canonical tables worth full DDL capture.
3. Export DDL for the filtered set with `scripts/athena/run_table_ddl_export.py`.
4. Compose or refresh the markdown knowledge doc with `scripts/dev/update_athena_table_ddl_knowledge.py`.

The markdown file is generated in part, not fully hand-written: the DDL section lives between fixed `<!-- DDL_SECTION:BEGIN -->` / `<!-- DDL_SECTION:END -->` markers so later re-exports replace only
that section and leave the narrative inventory intact.

## Prerequisite before step 1

This project does not yet have a resolved AWS SSO profile and target-tenant context for any new Athena database discovery/export run. Before using the Athena cache workflow, complete the tenant work
tracked in `docs/plan/tenant-registry/prompt.md` so the correct tenant, profile, and database context can be resolved explicitly instead of guessed.

QC-4 adds only the ported tooling and this convention doc. It does **not** populate or refresh any real `knowledge/*-tables.md` cache file in this worktree.

## Lightstep follow-up

The same cache idea applies on the Lightstep side: one durable knowledge file per project or service family capturing stable attribute names, grouping keys, and filtering conventions so future query
writing does not start from zero.

For the intended shape, see the read-only reference `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`. That Lightstep-side cache is a follow-up
convention only; QC-4 does not build it here.
