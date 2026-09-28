# Project taxonomy — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `PYTHON_DESIGN.md`. After each task: set `SHA:` on the
> task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

---

## PT-1 — `docs/guides/project-taxonomy.md`: five categories + `github_copilot` examples

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — new file

**What to implement:**

1. Header matching `docs/guides/git-multi-account-auth.md`'s tone (short intro paragraph, no plan-tracking checkboxes — this is a reference doc, not a story file).
2. A `## Categories` section defining exactly five categories, one paragraph each:
   - **Pipeline** — recurring, scheduled data collection/reporting with no open-ended investigation question. Example: `github_copilot/aws-access-cli` (cron-scheduled Athena adoption/session reports,
     SSO refresh).
   - **Continuous investigation** — an open-ended, ongoing data-gathering + analysis effort tied to a live product question, expected to run for months. Example:
     `github_copilot/ctap-smvod-session-report` (already a submodule).
   - **One-off investigation** — a bounded case with a start and an end (a specific incident, a specific third-party report). Example: `github_copilot/applauseInvestigation`,
     `github_copilot/mtn-zm-session-device-investigation`.
   - **Tool** — reusable software with its own interface/protocol, actively maintained and enhanced across many callers. Example: `github_copilot/oasis-athena-mcp` (MCP server),
     `github_copilot/mtn-network-traffic` (curl-to-Python converter).
   - **Experiment** — a short-lived probe answering one narrow question, expected to be thrown away or absorbed once answered. Example: `github_copilot/vod-asset-ingestion-mapping`,
     `github_copilot/vod-playback-timing-probe`.
3. Each category paragraph ends with one sentence distinguishing it from its nearest neighbor (pipeline vs. continuous investigation: scheduled+no open question vs. open question; one-off vs.
   experiment: bounded real-world case vs. throwaway probe) — this is the actual test a session applies, not just a label.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): define the five project categories`

---

## PT-2 — same doc: per-category folder skeleton + submodule-vs-plain-folder rule

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — append to the file created in PT-1

**What to implement:**

1. A `## Folder skeleton per category` table, columns `Category | Required files | Notes`, one row per PT-1 category:
   - Pipeline: `scripts/` (imports `src/lib/*` from `docs/plan/functional-code-taxonomy/`), `tests/`, a doc stating the schedule (what runs when, e.g. a cron expression or trigger description) — no
     `investigations/docs` (nothing to write up, it is not a case).
   - Continuous investigation: `AGENTS.md`-delta (or `.github/copilot-instructions.md` if a submodule), `session-info.md`, `TODO.md`, `investigations/{docs,data,queries}`, local `knowledge/` staging.
   - One-off investigation: same skeleton as continuous investigation but with a required `investigations/docs/<case>-executive-summary.md` and an explicit close-out step (archive once the case closes
     — do not leave it open-ended).
   - Tool: `src/`, `tests/`, its own `README.md`, no `investigations/` (it is not a case-tracking folder).
   - Experiment: starts in `scratch/` per this project's existing convergence rule (`scratch/SCRATCH.md`) — only gets a dedicated folder if/when it converges into a tool or gets absorbed into a
     pipeline/investigation; never starts as its own top-level folder.
2. A `## Submodule vs. plain folder` section stating the rule found during the 2026-09-28 audit: a folder becomes a real git submodule (own `.git`, own remote, own `.github/copilot-instructions.md` if
   it needs instructions distinct from the root's) when it is a **pipeline**, **continuous investigation**, or **tool** (independent commit cadence, benefits from scoped instructions); it stays a
   **plain folder** under the root repo when it is a **one-off investigation** or **experiment** (short-lived, no benefit from a separate remote, and per `CONTEXT.md`'s constraint this project has no
   folders yet needing that split — state this is the rule for *future* work, not a migration list).
3. Cross-reference `docs/plan/functional-code-taxonomy/` by name for "what code a pipeline/tool/investigation's `scripts/`/`src/` folder should import" — do not restate that story's module layout
   here.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): add folder skeletons and submodule-vs-folder rule`

---

## PT-3 — same doc: new-investigation checklist with mandatory prior-art search

**Files to change / create:**
- `docs/guides/project-taxonomy.md` — append to the file created in PT-1/PT-2

**What to implement:**

1. A `## Starting new work` checklist, numbered:
   1. Classify the work against the PT-1 category definitions — if it doesn't clearly fit one, stop and ask (per this project's global "don't assume — ask" rule) rather than picking the closest label.
   2. Delegate a sub-agent (the `explore` or `task` agent type — bounded, read-only) to search, in order: `docs/guides/`, `knowledge/` (once it exists as a folder), and `/Users/abhadra/github_copilot`
      (read-only reference) for prior art answering the same or a closely related question. Give the sub-agent the concrete question, not just a category name.
   3. If the sub-agent finds a match: reuse or extend it; do not create a new top-level folder duplicating it.
   4. If no match: create the folder using PT-2's skeleton for the classified category.
2. State explicitly why step 2 is delegated rather than done inline — same rationale as `docs/plan/scratch-script-registry/prompt.md`'s duplicate-check delegation (keeps the search cost off the main
   session's context, makes it a named auditable step) — this checklist is that same pattern applied at whole-project scope instead of single-script scope; do not re-justify it differently.

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): add new-work checklist with prior-art search`

---

## PT-4 — `scripts/dev/check_project_taxonomy.py` + tests

**Files to change / create:**
- `scripts/dev/check_project_taxonomy.py`
- `tests/dev/test_check_project_taxonomy.py`
- `tests/dev/__init__.py` if not already created by another story (per `AGENTS.md`'s package convention — check before creating a duplicate)

**What to implement:**

1. `CATEGORY_MARKERS: dict[str, tuple[str, ...]]` — for each PT-1 category, the marker file(s)/folder(s) from PT-2's skeleton that identify it (e.g. continuous/one-off investigation:
   `investigations/`; tool: `src/` + own `README.md`; pipeline: `scripts/` + a schedule doc — use a `Protocol`-free simple mapping here, this is a small audit script, not a domain model warranting
   `PYTHON_DESIGN.md`'s DI treatment).
2. `classify_dir(path: Path) -> str | None` — checks a top-level directory against `CATEGORY_MARKERS`, returns the matched category name or `None` if no marker matches.
3. `find_unclassified_dirs(root: Path, ignore: tuple[str, ...]) -> list[Path]` — lists top-level directories under `root` excluding a fixed ignore set (`.git`, `docs`, `scripts`, `tests`, `scratch`,
   `logs`, `tmp`, `tooling`, `.github`) whose `classify_dir` result is `None`.
4. `main()` — `argparse` with `--root` (default: repo root); prints each unclassified directory with a one-line hint to run PT-3's checklist before deciding its category; exits non-zero only if asked
   with `--strict` (default off — this is advisory, not a commit-blocking gate, since no folders exist yet to enforce against).

**Tests (no network, no real external directories outside `tmp_path`):**
- `test_classify_dir_matches_investigation_marker` / `test_classify_dir_returns_none_for_unrecognized_layout`
- `test_find_unclassified_dirs_skips_ignored_and_flags_unmarked` — fixture tree with one classified dir, one unclassified dir, and one ignored dir (e.g. `docs/`); assert only the unclassified one is
  returned.

**Commit:** `feat(project-taxonomy): add check_project_taxonomy.py audit script`

---

## PT-5 — `AGENTS.md` + `CONTEXT.md` pointer lines

**Files to change / create:**
- `AGENTS.md` — add one pointer line (placement: near the existing docs/plan story-tracking section, per its existing structure)
- `CONTEXT.md` — add one line to "What Exists"

**What to implement:**

1. `AGENTS.md`: one sentence pointing to `docs/guides/project-taxonomy.md` as the reference for classifying new work and picking its folder skeleton before creating any new top-level folder. No
   taxonomy content duplicated into `AGENTS.md` itself.
2. `CONTEXT.md`: one new bullet under "What Exists" in the same style as the existing `tenant-registry`/`query-catalog` bullets — story slug, one-line summary, current status (implemented once PT-1
   through PT-4 are all checked; reference the first unchecked task id if not yet fully done at the time this task runs).

**Tests:** none — docs-only.

**Commit:** `docs(project-taxonomy): point AGENTS.md and CONTEXT.md at the new guide`
