# Tenant registry — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: none — story complete.**

- [x] **TR-1** — Scratch probe: tenant resolution + real Lightstep MCP round-trip | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms MCP query result matches expected
  opco | SHA: 2140cc8
- [x] **TR-2** — `config/tenants.yaml`: canonical MTN tenant config | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 78880e5
- [x] **TR-3** — `src/tenant_registry/`: `TenantConfig`/`TenantRegistry`/`QueryTarget` implementers | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 7ad3b7d
- [x] **TR-4** — `scripts/resolve_tenant.py` CLI wrapper | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 77a6e79
- [x] **TR-5** — `docs/guides/tenant-resolution.md` + `AGENTS.md` pointer | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: 14aa88b
- [x] **TR-6** — Tests for registry, query targets, and CLI | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: ea62e1e

## Story done when

- **TR-1** — A scratch script resolves SA (dedicated project) and one of Ghana/Zambia (shared project) to their correct Lightstep project + filter, and a real `query_spans`/`list_services` MCP call
  using those resolved values returns opco-appropriate data (confirmed by a human), before any production code exists.
- **TR-2** — `config/tenants.yaml` holds all 4 MTN opcos with all 4 ID types, Lightstep project/region, `shared_project` flag, and disambiguation attribute — no tenant data left in Python or Markdown.
- **TR-3** — `TenantRegistry` loads only from `config/tenants.yaml` (no hardcoded seed list); each `QueryTarget` implementer resolves its own system without branching on a `system` string anywhere.
- **TR-4** — `scripts/resolve_tenant.py --system <lightstep_go|matisse|athena> --tenant <any known id>` prints one line of JSON on success, or exits non-zero with a clear error listing valid ids.
- **TR-5** — `AGENTS.md` contains exactly one new line pointing to `docs/guides/tenant-resolution.md`; the guide states the CLI-first protocol and never inlines tenant values.
- **TR-6** — `pytest` covers: registry lookup by each id type + unknown-id error; each `QueryTarget`'s happy path + the shared-project-without-`busUnitId` rejection; one CLI smoke test (success +
  failure exit code).

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised (a plan index file for a single story, the epic `README.md` story list
for an epic sub-story) and add one line to your backlog/session-log file. When the whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
