# Query catalog workflow

Use this guide for Athena and Lightstep query work. Start with `queries/README.md` for the catalog layout and file conventions; this guide covers the decision flow for reusing an existing query,
writing a new template, and deciding when a query should become a script.

## 1. Reuse before you write

Before writing any new query, scan the relevant catalog index first: `queries/athena/index.md` for Athena SQL or `queries/lightstep/index.md` for Lightstep TQL. The index is the cheap, single-file
check for whether the query shape already exists.

If a matching shape is already listed, reuse that template instead of writing new SQL or TQL. Fill in different `{{placeholder}}` values for the case at hand rather than creating a near-duplicate file
with different literal IDs, dates, or other parameters.

## 2. For Athena, check cached schema before re-deriving it

Before re-deriving Athena table or column shape from a live query, check the relevant `knowledge/<project>-athena-<db>-tables.md` DDL cache if one exists. Use the cached DDL reference as the source
for table and column shape, and only fall back to live rediscovery when the needed schema is not already documented there.

## 3. When no matching template exists, create one

If the relevant `index.md` has no matching query shape, add a new parameterized template from the start. Do not save a literal one-off query with baked-in IDs, dates, households, devices, or other
case-specific values.

For Athena queries, save the template under `queries/athena/<slug>.sql`. For Lightstep queries, save the template under `queries/lightstep/<slug>.md` with the native TQL block preserved. In either
case, add the matching row to that source's `index.md` so the next session can discover it by scanning one file instead of re-deriving it.

## 4. Promote to a script only for post-processing logic

A parameterized query template is enough for parameter-only reuse. Promote query work into a script such as `scripts/athena/` or another established analysis-script location only when reuse needs
actual post-processing logic after the query runs: joins across exports, pivoting, report generation, normalization, or similar code.

This is a directly observable trigger, not a reuse-count trigger. The question is whether the reuse now needs code beyond substituting `{{placeholder}}` values. It is not "promote after N reuses,"
because query execution happens outside this assistant and is run manually, so a reliable reuse count cannot be tracked here.
