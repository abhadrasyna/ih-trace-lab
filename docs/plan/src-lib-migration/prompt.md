# Src-lib migration — prompt (router)

Central entry point for this epic. Your work-session entry skill loads this file, **not** a sub-story `prompt.md`. Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else, then follow the
steps below to find and run exactly one task.

**Origin:** `README.md` in this folder — the epic index. Read it if you have not this session; it carries the scope decisions, the architecture diagram, the ordered story list, and the cross-cutting
constraints this router's logic depends on.

**Hard gate before Step 1:** this whole epic is blocked on `docs/plan/functional-code-taxonomy/` FCT-1 (module map) and FCT-2 (`athena`/`report_render`/`har` `Protocol` skeletons) landing — FCT-7
(`PathResolver`) additionally gates any story that resolves file paths. Check `docs/plan/functional-code-taxonomy/tasks.md` first. If FCT-1/FCT-2 are still unchecked, **stop here** and report that
this epic cannot start yet; do not improvise a `Protocol` shape this epic's stories weren't written against.

---

## Step 1 — find the next task

Story order is fixed — it is the row order of the **Stories** table in this folder's `README.md`. Keep this list identical to that table:

1. `athena-lib-integration/` — submodule `athena-mcp-server` + thin adapter
2. `report-render-lib-migration/` — port CSV/report writers
3. `har-lib-migration/` — port HAR-entry loaders
4. `auth-lib-migration/` — consolidate AWS SSO auth (blocked by: `athena-lib-integration` complete — reuses `athena_runner.sso_auth`'s shape as prior art)
5. `csv-io-lib-migration/` — consolidate raw CSV I/O
6. `curl-to-python-lib-migration/` — consolidate curl→Python conversion

Do not jump ahead even if a later story looks more urgent.

Open `athena-lib-integration/tasks.md`. If it has any unchecked `- [ ]` line, the first one (top to bottom) is your task — stop searching, go to Step 2. Only if every box in a story's `tasks.md` is
checked: move to the next story in the list above, first unchecked line is your task. And so on. If every sub-story `tasks.md` is fully checked, the epic is complete — say so and stop; do not invent
new work.

## Step 2 — confirm you are the right owner

The task line carries `| Owner: … | Model: … | Review: … | SHA: …`. Read it before doing anything.

- If `Owner` does not match the agent running this session, **stop** and report: which task you found, what it is routed to, and that this session should not implement it.
- If `Model` names a model this session is not running, say so before proceeding.
- Note the `Review` gate now — if it names a review agent or step, that gate is mandatory before commit per this project's own `AGENTS.md`.

## Step 3 — load the sub-story context

Read that story's own `prompt.md` for its hard constraints (test-gate command, non-fatal contracts, coordination checks) and its `stories.md` for the task's full spec, including its class/sequence
diagrams. `athena-lib-integration` additionally requires reading `/Users/abhadra/myWork/myOffice/athena-mcp-server/CONTEXT.md` before touching the submodule — that repo has its own known open item
(the `aws-access-cli` sibling-checkout namespace-package merge) this epic must not silently paper over.

## Step 4 — implement, verify, record

Follow the sub-story `prompt.md`'s protocol: implement, run the test gate, run the `Review` gate if flagged, commit via your project's commit process (execute it, do not just draft the message), set
`SHA:` on the task line + tick the box, update this epic's `README.md` story-list status column, add one line to your backlog/session-log file.

**Stop.** One task per session — do not proceed to the next unchecked item in any story.
