# Knowledge: MTN Lightstep Identity and Session Investigation Methodology

## Read this first when

Consult this before writing a new Lightstep MCP query, before tracing a device/household/OAuth-session identity flow, or before assuming a DRM trace propagates cleanly across the EU/US regional
boundary.

## Lightstep MCP tool hard rules

| Tool | Use it for | Hard rule |
| --- | --- | --- |
| `query_spans` | discovery: find candidate spans / trace IDs | Do **not** use `spans count | delta | ...` pipeline syntax here |
| `query_timeseries` | aggregation, counting, group-by pipelines | This is the **only** tool that accepts the pipeline syntax |
| `get_stored_trace` | full span attributes and child spans | Requires hex IDs, not the decimal IDs returned by the query tools |
| `list_attributes` | attribute catalog | Treat as broken; rely on reference docs instead |

Reusable rules from the shared notes:

- Use RFC3339 timestamps.
- Convert decimal IDs to hex before `get_stored_trace`.
- Expect adaptive sampling; repeated 404s from `get_stored_trace` are often a retention/sampling limit, not a query bug.
- Stored-trace retention is about seven days.

## Client-identity methodology

The `client-identity-investigation` playbook is household-driven:

1. start from `householdId`;
2. enumerate all `clientId` values associated with that household;
3. inspect the operation history for each client ID (`oauth-register`, `oauth-authorize`, `oauth-authorize-end`, `oauth-token`, `oauth-revoke`);
4. summarize the registration IPs, grant-type history, and revoke/logout behaviour.

The key fact it preserves is that `clientId` is session-lifecycle state, while `deviceId` is the stable hardware anchor. Track a physical device by `deviceId`, not by whatever `clientId` it most
recently received.

## Device-flow methodology

The `device-flow-analysis` playbook starts from `PROJECT_ID` + `DEVICE_ID` and reconstructs the device's backend journey:

1. discover playsession-related traces for the device;
2. pull the full distributed traces;
3. walk the request/response timeline across CTAP and downstream services;
4. extract the household and session identifiers that are only exposed later in the flow.

This playbook is designed to chain into client identity. Its Step 8 explicitly hands the derived `HOUSEHOLD_ID` and time window to the client-identity playbook so the device-flow session and the
identity-lifecycle session stay joined.

## OAuth ⇄ session-guard interleave methodology

The `oauth-session-guard-interleave` playbook is not a single-trace exercise. It needs an interleaved timeline built from two projects:

- Matisse / client-identity OAuth spans
- GO-platform `session-guard` refresh spans for the same device

Inputs are `DEVICE_ID` plus a `LOOKBACK` window. The method is:

1. gather the OAuth spans for the device in Matisse;
2. gather the `session-guard` refresh spans for the same window;
3. merge and sort them into one timeline.

That interleave is what reveals whether token issuance, session refresh, or revoke behaviour happened first; no single trace ID spans both sides.

## DRM cross-region methodology

The `drm-cross-region-investigation` playbook records the most important regional fact in this workspace:

- EU `go-mdrmfe` and US `mcs-mdrm-production` are two separate Lightstep projects.
- They do **not** share trace IDs or span IDs across the regional boundary.
- Correlation therefore has to use business attributes (`drmAuthToken.jti`, `contentId`, `deviceId`, `sessionId`, tenant) plus a tight time window.

The recommended method is:

1. start on the EU `go-mdrmfe` span and capture the business identifiers plus outbound POST timestamp;
2. look in the US project for the matching attributes within a narrow time window;
3. walk the US chain only after the cross-region match is confirmed.

Worked examples of that exact technique now live in:

- `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md`
- `knowledge/mtn-tenant-identifiers-and-code-flow.md`

## What this file does not port

The source playbooks are executable prompts with wrappers such as "paste this into Copilot CLI chat" and usage-trigger phrasing. Those invocation shells remain in
`github_copilot/investigations/instructions/`. This file keeps only the reusable facts and methodology.

## Source

Source paths: `/Users/abhadra/github_copilot/investigations/instructions/lightstep-mcp-tool-notes.md`, `/Users/abhadra/github_copilot/investigations/instructions/client-identity-investigation.md`,
`/Users/abhadra/github_copilot/investigations/instructions/device-flow-analysis.md`, `/Users/abhadra/github_copilot/investigations/instructions/oauth-session-guard-interleave.md`, and
`/Users/abhadra/github_copilot/investigations/instructions/drm-cross-region-investigation.md`. These files are read-only reference, not a shared codebase.
