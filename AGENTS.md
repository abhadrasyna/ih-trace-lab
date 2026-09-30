# <project-name> — AI Assistant Pre-Task Protocol

> Auto-loaded at session start. Keep this file thin — push bulky detail into a lazily-loaded skill once there's enough of it to warrant one, once this file stops fitting on one screen.

## Step 1 — Read CONTEXT.md first

Read `CONTEXT.md` before writing any code. State `CONTEXT.md ✓` verbatim in your first user-facing response — reading the file without the visible acknowledgment leaves no record this step ran.

<!--
Add a module-AGENTS.md index row here once the project has multiple modules each with their own auto-loaded AGENTS.md. Not needed at Tier 0.

Add a DB_REGISTRY.md pointer here once the project writes to a database with more than one or two tables, or once "which table holds X" stops being obvious from the code. Not needed at Tier 0. -->

<!-- INSERT: rule0 -->

## Step 2 — Confirm scope

If the prompt does not name specific files, ask before starting. One clarifying question beats building the wrong thing.

**Before assuming code is wanted at all:** a project idea that sounds like software doesn't mean code should be written yet. Confirm whether this session wants an implementation (a real `src/`, a
chosen language/storage/ framework), or is still in design/planning (markdown notes, a `docs/` folder, a story to write up) — do not default to scaffolding a package just because the prompt named a
project idea. If code is confirmed wanted: confirm which files change, and tests required (default: yes).

<!--
Add a Step 2b council checkpoint here once a decision surfaces that is (1) load-bearing and costly to reverse, (2) has two defensible approaches with materially different outcomes, and (3) spans
multiple disciplines at once — this can fire on day one for a high-stakes small project (e.g. tax-bracket logic), it is not gated on project size. Until then, skip straight to Step 3. -->

<!-- INSERT: stakes -->

## Step 3 — State plan, wait for go-ahead

> Plan: [one sentence] → touches [file1, file2] → tests in [test file] → commit. Proceed?

If the plan touches more than 2 files, wait for explicit go-ahead.

<!-- INSERT: multi-surface -->

<!-- marker: tier1 -->
## Story/epic planning (`docs/plan/`)

Work above a single-sitting fix is tracked as a story (one coherent goal) or epic (2+ related stories) under `docs/plan/<slug>/` — see `docs/plan/README.md` for the file-set conventions and
`docs/plan/_TEMPLATE/README.md` for how to start one (`cp -r docs/plan/_TEMPLATE/story docs/plan/<slug>`). Structure and checkbox consistency are enforced at commit time by the
`docs-plan-story-structure`/`docs-plan-checkbox-consistency` pre-commit hooks (see `tooling/docs-plan/`) — a malformed plan folder fails the commit, not a later review. Before creating any new
top-level work folder, classify it with `docs/guides/project-taxonomy.md` and use that guide's folder skeleton for the chosen category.
<!-- INSERT: tier1 -->

## Step 4 — Tests are mandatory

Every public function needs one happy-path test + one error/edge-case test. No network in tests.

<!-- INSERT: test-runner -->

## Step 5 — Close the phase (docs → tests → commit)

A phase is not complete until all three are done.

**5a — Update docs:** `CONTEXT.md` "What Exists" if new files were added.

<!-- INSERT: state-freshness -->

<!-- INSERT: md-organize -->

**5b — Verify tests green** before committing.

**5c — Commit:** use the `commit` skill's message format. The commit must be executed, not drafted — a written-out message is not a commit.

<!--
Add a mandatory code-reviewer subagent gate here once the project is large or high-stakes enough to warrant an isolated review pass before every commit (Tier 2). Until then, review the diff yourself
before committing. -->

<!-- INSERT: weekly-audit -->

## Python conventions

<!--
Delete this whole section if the project isn't Python. If it is, keep only what's actually true for this project — do not carry over Decimal/asyncio-daemon specifics unless the project actually
touches money or runs a long-lived concurrent service. -->

- Python 3.10+, type hints on all public function signatures.
- Functions 10–20 lines typical. Split only when it improves clarity.
- `Decimal` for all monetary values, never `float` — only if this project touches money.
- Offline-first tests: zero network, zero real tokens, zero real DBs by default.

<!-- marker: python -->
- Type hints on **all** public function signatures, not just new/touched ones.
- `(str, Enum)` for string enums — never `StrEnum` (py3.11+ only, this overlay targets 3.10+).
- `Decimal` for monetary values, opt in only if this project actually touches money — do not add it speculatively.
- `pyproject.toml` + `requirements.txt`/`requirements-dev.txt` (not a `pyproject.toml`-only dependency model).
- Call `setup_logging()` from `logs/setup_logging.py` once at process start; never `logging.basicConfig` elsewhere, never bare `logging.getLogger(__name__)` in `scripts/` (loses module context when
  run as `__main__`).
- Every new package directory under `src/`, `scripts/`, or `tests/` needs an `__init__.py`, even a one-line comment.
- Design principles beyond the basics (SOLID as checkable triggers, named patterns): `PYTHON_DESIGN.md`, load on trigger only — not resident here.
- `docs/guides/functional-code-taxonomy.md` is where this project applies `PYTHON_DESIGN.md`'s SRP/OCP/DIP triggers concretely to shared-lib boundaries; read it when shaping or reviewing `src/lib/*`.
<!-- INSERT: python -->

## Domain conventions

<!--
Delete this whole section if the project doesn't touch Athena/tenant investigation work. Keep only what's actually true for this project. -->

<!-- INSERT: athena -->

- Before any Lightstep/Matisse/Athena MCP call, run `python scripts/resolve_tenant.py ...` first and follow `docs/guides/tenant-resolution.md`; never guess tenant ids or project context.
<!-- INSERT: investigations -->

## Git conventions

- Commit messages: imperative mood, ≤60 char subject. Body explains why, not what.
- Never amend pushed commits. New commit to fix, not force-push.
- Stage specific files — never `git add .` blindly.

## Markdown formatting

Write prose paragraphs filled to ≤200 characters per line, not hard-wrapped at ~80. A paragraph is one logical block of text with no mid-sentence line breaks up to the 200-char cap — reflow it as a
single flowing block, don't hand-wrap at whatever width happens to look right in this editor. This applies to every markdown file in this project (`AGENTS.md`, `CONTEXT.md`, `README.md`, skill files,
any future `docs/`), from the first file written. Code blocks, tables, and list-item structure are unaffected — this is a prose-wrapping rule, not a whole-file reformat.

<!--
Once this project is identified as Python (see Python conventions above), add a reflow/check tool + pre-commit hook to enforce this automatically instead of relying on manual discipline. Not needed at
Tier 0 — the written rule above is the whole mechanism until then. -->

## No throwaway code in production folders

A quick POC or exploration always starts in `scratch/` first (see `scratch/SCRATCH.md`) and only graduates to `src/`/`scripts/` once it's proven, via the convergence rule documented there. Before
writing a new scratch script, the duplicate-check + stub-creation step is delegated per `scratch/SCRATCH.md`'s "Registry & duplicate-check" section. This is a hard requirement, not just an available
option.
