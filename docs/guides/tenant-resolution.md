# Tenant resolution protocol

Before invoking any Lightstep, Matisse, or Athena MCP tool for a named opco, resolve that tenant locally first with `python scripts/resolve_tenant.py --system <lightstep_go|matisse|athena> --tenant
<identifier>`. Use the JSON it prints as the source of truth for the external call. If the command exits non-zero, stop and ask rather than guessing, retrying with a hardcoded value, or re-deriving
ids from memory.

`config/tenants.yaml` is the only place tenant data lives. This guide intentionally does not duplicate ids or project names; it defines the protocol for turning a known identifier into the right query
context.

## CLI-first workflow

1. Start from any known tenant identifier accepted by the registry: code, GO id, Matisse project id, Matisse client tenant id, or Athena tenant id.
2. Run the resolver via `bash`, for example `python scripts/resolve_tenant.py --system lightstep_go --tenant <identifier>`.
3. Read the single-line JSON response and copy its fields directly into the MCP call you are about to make.
4. If stdout is empty or stderr reports an error, do not continue with the MCP tool until the tenant identifier is corrected.

## Shared-project case

Some MTN opcos share a Lightstep project. For that case, the CLI's `filter` output is load-bearing: it is what narrows a shared infrastructure project down to the intended opco's request traffic. In
other words, the project name alone is not enough; use both the returned `project` and the returned `filter` together.

TR-1's probe also showed an operational gotcha worth preserving: on shared projects, a narrow service+time-window query can return empty even when the tenant filter is correct, because the
disambiguation attribute is not present on every service's spans. If that happens, keep the resolved tenant filter but widen to a project-wide, multi-hour window first, then inspect a matching trace.

## System outputs

- `lightstep_go` returns a Lightstep project, region, and either `null` or a required tenant-disambiguation filter.
- `matisse` returns the Matisse project id and client tenant id.
- `athena` returns the Athena database, profile, and region.
