# `queries/` — Athena and Lightstep query catalog

A durable, deduplicated catalog of Athena and Lightstep queries, so a query written once (real token cost: table discovery, join-key reasoning, trial-and-error against real schema) never has to be
re-derived, and never gets re-typed as a near-duplicate with only literal IDs changed.

## Layout

```
queries/
  athena/
    index.md          # one row per distinct query shape — read this first, always
    <slug>.sql           # parameterized template ({{placeholder}} params), header comment: purpose/tables/params/source
    <slug>.md             # optional — only when there's real why/found narrative beyond the index row
  lightstep/
    index.md          # same pattern, keyed on service/operation/attribute instead of tables/columns
    <slug>.md             # native TQL block (Lightstep queries aren't plain SQL), same header convention
```

## Core rules

### 1. Check `index.md` before writing anything new

`queries/athena/index.md` and `queries/lightstep/index.md` are the only files that have to be scanned for the "does this already exist" check — deliberately small, one row per query shape, not per
literal query. Check the relevant `index.md` first, every time, before writing new SQL/TQL.

### 2. Save as a parameterized template, never a literal one-off

Use `{{household_id}}`, `{{date}}`, `{{device_id}}`, etc. from the first write — this is what actually prevents duplication. A query saved with baked-in literals gets re-typed with new literals next
time; a template gets reused.

### 3. Promote to a script only when reuse needs post-processing logic

Promote to a script (CSV joins, pivoting, report generation) only when reuse needs that kind of logic — not merely different parameter values. A plain parameterized query file is sufficient forever
for parameter-only reuse; there is no "count N reuses, then promote" step, because query execution happens outside this assistant (the user runs queries manually) and usage can't be reliably counted.
See `docs/guides/query-catalog.md` for the full workflow once it exists.

## Before writing new Athena SQL

Check the relevant `knowledge/<project>-athena-<db>-tables.md` DDL cache before re-deriving a table's columns from a live query, once one exists (see `docs/plan/query-catalog/` task QC-4) — don't
re-discover schema that a cached DDL doc already has.
