# Query catalog — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.
> Full implementation rules live in `AGENTS.md` and `PYTHON_DESIGN.md`.
> After each task: set `SHA:` on the task line + tick the box, update the story status
> summary, add one line to your backlog/session-log file.

---

## QC-1 — `queries/README.md`: folder purpose, layout, and core rules

**Files to change / create:**
- `queries/README.md` — new

**What to implement:**

1. State the folder's purpose in one paragraph: a durable, deduplicated catalog of Athena and Lightstep queries, so a query written once (real token cost: table discovery, join-key reasoning,
   trial-and-error) never has to be re-derived, and never gets re-typed as a near-duplicate with only literal IDs changed.
2. Document the layout:
   ```
   queries/
     athena/
       index.md          # one row per distinct query shape — read this first, always
       <slug>.sql          # parameterized template ({{placeholder}} params), header comment: purpose/tables/params/source
       <slug>.md            # optional — only when there's real why/found narrative beyond the index row
     lightstep/
       index.md          # same pattern, keyed on service/operation/attribute instead of tables/columns
       <slug>.md            # native TQL block (Lightstep queries aren't plain SQL), same header convention
   ```
3. State the three core rules explicitly, each as its own subsection:
   - **Check `index.md` before writing anything new.** It is the only file that has to be scanned for the "does this already exist" check — deliberately small, one row per query shape, not
     per literal query.
   - **Save as a parameterized template, never a literal one-off.** `{{household_id}}`, `{{date}}`, `{{device_id}}`, etc. from the first write — this is what actually prevents duplication (a
     query saved with baked-in literals gets re-typed with new literals next time; a template gets reused).
   - **Promote to a script only when reuse needs post-processing logic** — CSV joins, pivoting, report generation — not merely different parameter values. A plain parameterized query file is
     sufficient forever for parameter-only reuse; there is no "count N reuses, then promote" step, because query execution happens outside this assistant (the user runs queries manually) and
     usage can't be reliably counted. Point to `docs/guides/query-catalog.md` (QC-5) for the full workflow once it exists.
4. Note that a query's underlying schema should be checked against the relevant `knowledge/<project>-athena-<db>-tables.md` DDL cache before writing new Athena SQL, once one exists (see QC-4) —
   don't re-discover a table's columns from a live query when a cached DDL doc already has it.

**Tests:** none — docs-only change.

**Commit:** `docs(query-catalog): add queries/README.md`

---

## QC-2 — `queries/athena/`: harvest reference catalogs into deduplicated templates + `index.md`

**Files to change / create:**
- `scripts/dev/harvest_athena_query_catalog.py` — the harvest script
- `queries/athena/index.md` — generated output
- `queries/athena/<slug>.sql` — one per distinct query shape, generated output

**What to implement:**

1. `extract_sql_blocks(markdown_path)` — parse a `QUERY_CATALOG.md`-style file (fenced ` ```sql ` blocks), pairing each block with the nearest preceding heading (issue/section title) and any
   immediately-following `**Why:**`/`**Found:**` prose. Return a list of raw entries; skip files with no fenced SQL blocks (log and continue, do not raise — one malformed reference file must
   not abort the whole harvest).
2. `normalize_to_shape(sql)` — reduce a raw SQL query to a dedup key: table name(s) referenced + the set of column names appearing in `WHERE`/`ON`/`GROUP BY` clauses, literal values stripped.
   Two queries against the same table(s) with the same filter/join columns but different literal values (e.g. a different `device_id`, a different date) must normalize to the same shape.
3. `templatize(sql)` — rewrite literal values (quoted date/ID/string literals in `WHERE`/`ON` clauses) as `{{snake_case_placeholder}}`, inferring the placeholder name from the column being
   compared (e.g. `device_id = '...'` → `{{device_id}}`). Leave structural SQL (table names, column lists, `SELECT *`, `ORDER BY`) untouched.
4. `build_catalog(paths)` — read all 3 reference `QUERY_CATALOG.md` files (paths passed explicitly, not hardcoded), extract + normalize + templatize every SQL block, group by shape, and for
   each shape produce: a slug (kebab-case, derived from the primary table name(s) + the key filter column(s)), the templated SQL, the list of origin files/sections it was found in, and a
   one-line purpose (from the nearest `**Why:**` prose, or the heading text if no `**Why:**` is present).
5. `write_catalog(root, catalog)` — writes `queries/athena/<slug>.sql` (templated SQL + a header comment: purpose, tables, params, origin issues) for each shape, and `queries/athena/index.md`
   (one row per shape: `Slug | Tables | Key params | Purpose | Source`), sorted by slug.
6. `main()` — `argparse` with `--sources` (one or more `QUERY_CATALOG.md` paths, default: the 3 reference files' real paths under `/Users/abhadra/github_copilot`, overridable for testing) and
   `--root` (default: repo root). Runs the full pipeline, prints how many shapes were written and how many raw queries were deduplicated into each.

**Tests:** written in QC-6, not here.

**Commit:** `feat(query-catalog): harvest Athena reference catalogs into queries/athena/`

---

## QC-3 — `queries/lightstep/`: harvest `lightstep-query-templates.md` into templates + `index.md`

**Files to change / create:**
- `scripts/dev/harvest_lightstep_query_catalog.py` — the harvest script
- `queries/lightstep/index.md` — generated output
- `queries/lightstep/<slug>.md` — one per template, generated output

**What to implement:**

1. `extract_templates(markdown_path)` — parse `lightstep-query-templates.md`'s structure: each `##`/`###` section with a fenced (unlabeled, TQL) code block is one template. Capture the
   section title, the TQL block, the `**Purpose:**` line, the `Tool:` line (e.g. `query_timeseries`), and the `**Save exports as:**` line, when present. Unlike the Athena source, this file's
   queries are **already parameterized** (`<DEVICE_ID>`, `<Applause ID>`, etc.) — no literal-stripping step is needed here, only reformatting `<PLACEHOLDER>` to this project's `{{placeholder}}`
   convention for consistency with `queries/athena/`.
2. `slugify(title)` — derive a kebab-case slug from the section title (e.g. "sm-vod Session Inventory by Device" → `smvod-session-inventory-by-device`).
3. `build_catalog(path)` — run `extract_templates` + `slugify` over the one source file, returning one entry per template (no dedup pass needed — the source file has no repeated shapes to
   collapse, unlike the Athena catalogs).
4. `write_catalog(root, catalog)` — writes `queries/lightstep/<slug>.md` (the templated TQL block, `Purpose`, `Tool`, and `Save exports as` convention, plus a `Source:` line pointing back at
   the origin file) and `queries/lightstep/index.md` (one row per template: `Slug | Service/tool | Purpose | Source`), sorted by slug.
5. `main()` — `argparse` with `--source` (default: the real `lightstep-query-templates.md` path under `/Users/abhadra/github_copilot`, overridable for testing) and `--root` (default: repo
   root). Prints how many templates were written.

**Tests:** written in QC-6, not here.

**Commit:** `feat(query-catalog): harvest lightstep-query-templates.md into queries/lightstep/`

---

## QC-4 — `knowledge/`: port (not run) DDL-cache tooling + `knowledge/README.md`

**Files to change / create:**
- `scripts/athena/discover_athena_tables.py` — ported from `oasis-athena-mcp/scripts/discover_athena_tables.py`
- `scripts/athena/run_table_ddl_export.py` — ported from `oasis-athena-mcp/scripts/run_table_ddl_export.py`
- `scripts/dev/update_athena_table_ddl_knowledge.py` — ported from `/Users/abhadra/github_copilot/scripts/update_athena_table_ddl_knowledge.py`
- `knowledge/README.md` — new

**What to implement:**

1. Port the 3 scripts named above into this project, adapting only what's needed to fit `AGENTS.md`'s Python conventions (type hints, no hardcoded paths/IDs — they already take these as
   `argparse` flags in the source, per its own docstring). Do not invoke AWS/Athena from this task — porting is a file copy + adaptation, not a live run.
2. `knowledge/README.md` documents: (a) the convention — one `knowledge/<project>-athena-<db>-tables.md` file per Athena database, holding a generated DDL reference section plus a
   hand-written categorized table inventory, mirroring `oasis-athena-mcp/docs/table-ddl-knowledge-guide.md`'s 4-step workflow (discover tables → filter to canonical tables → export DDL →
   compose the doc); (b) that step 1 requires a resolved AWS SSO profile/tenant for the target database, which this project does not yet have — link `docs/plan/tenant-registry/prompt.md` as
   the explicit prerequisite, and state that this task does not populate any real `knowledge/*-tables.md` file, only the tooling to do so once that prerequisite lands; (c) the same convention
   applies to a future Lightstep-side knowledge cache (project/service IDs, attribute names — see `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` for the shape) —
   named here as a follow-up, not built by this task.

**Tests:** none — this task ports existing, already-tested infra scripts and writes one docs file; no new logic is introduced.

**Commit:** `chore(query-catalog): port Athena DDL-cache tooling, add knowledge/README.md`

---

## QC-5 — `docs/guides/query-catalog.md` protocol doc + `AGENTS.md` pointer

**Files to change / create:**
- `docs/guides/query-catalog.md` — new
- `AGENTS.md` — one new sentence in the existing "No throwaway code in production folders" paragraph

**What to implement:**

1. `docs/guides/query-catalog.md` states the end-to-end workflow for both writing a new query and reusing an existing one:
   - Before writing any new Athena/Lightstep query: check `queries/athena/index.md` or `queries/lightstep/index.md` first (cheap, single-file scan); if a matching shape exists, reuse its
     template with different `{{placeholder}}` values instead of writing new SQL/TQL.
   - For Athena specifically: check the relevant `knowledge/<project>-athena-<db>-tables.md` DDL cache before re-deriving table/column shape from a live query.
   - If no matching template exists, write one: parameterized from the start, saved under the correct `queries/<source>/` folder, with an `index.md` row.
   - Promote to a script (`scripts/athena/` or wherever a similar analysis script already lives) only when reuse needs actual post-processing logic — not for parameter-only reuse. State this
     is a directly observable trigger (does the reuse need joins/pivoting/report code), not a reuse-count trigger, and say why: query execution happens outside this assistant, run manually, so
     a reuse count can't be reliably tracked.
2. Add exactly one new sentence to `AGENTS.md`'s existing "No throwaway code in production folders" paragraph pointing at this new guide for the Athena/Lightstep query case specifically (mirror
   the tone of the existing pointer sentences already in that file — one line, no mechanics inlined into `AGENTS.md` itself).

**Tests:** none — docs-only change.

**Commit:** `docs(query-catalog): add docs/guides/query-catalog.md, point AGENTS.md at it`

---

## QC-6 — Tests for QC-2/QC-3 harvest scripts

**Files to change / create:**
- `tests/dev/test_harvest_athena_query_catalog.py`
- `tests/dev/test_harvest_lightstep_query_catalog.py`
- `tests/dev/__init__.py`, `tests/__init__.py` (if not already created by an earlier story — per `AGENTS.md`'s package convention, every new package directory under `tests/` needs an
  `__init__.py`)

**What to implement (per `AGENTS.md` Step 4 — one happy-path + one edge/error test per public function, no network, no real files outside `tmp_path`):**

- `test_harvest_athena_query_catalog.py`:
  - `test_extract_sql_blocks_pairs_heading_and_why_found` / `test_extract_sql_blocks_skips_file_with_no_sql_blocks` — a fixture markdown file under `tmp_path` with no fenced SQL returns an
    empty list, does not raise.
  - `test_normalize_to_shape_collapses_same_table_and_columns_different_literals` — two fixture queries against the same table/filter columns but different literal device IDs/dates normalize
    to the same shape key.
  - `test_templatize_replaces_literals_not_structure` — a fixture query's `WHERE device_id = '...'` becomes `WHERE device_id = '{{device_id}}'`; its `SELECT *`/table name/`ORDER BY` are
    unchanged.
  - `test_build_catalog_deduplicates_across_two_source_files` (happy path: two fixture `QUERY_CATALOG.md` files, each containing the same query shape with different literals, produce exactly
    one shape with both files listed as origins) / `test_build_catalog_handles_one_malformed_source_file` (edge case: one fixture file has a valid SQL block, the other has none — the harvest
    still returns the valid shape, does not raise).
- `test_harvest_lightstep_query_catalog.py`:
  - `test_extract_templates_captures_purpose_tool_and_save_path` (happy path against a small fixture mirroring `lightstep-query-templates.md`'s structure) / `test_extract_templates_skips_section_with_no_code_block`
    (edge case: a `##` section with prose but no fenced block is skipped, not raised).
  - `test_slugify_produces_kebab_case` (happy path) / `test_slugify_handles_punctuation_and_repeated_dashes` (edge case: a title with `×`/parentheses/multiple spaces still produces a clean
    single-dash slug).

**Commit:** `test(query-catalog): cover harvest_athena_query_catalog and harvest_lightstep_query_catalog`
