# TR-1 tenant Lightstep probe findings

## Resolution outputs

- South Africa (`iye9omdf`) resolves to project `mcs-go-prod-iye9omdf-eu`, region `EU`, and no disambiguation filter.
- Ghana (`apbyfj9d`) resolves to shared project `mcs-go-prod-mtn-1-eu`, region `EU`, and filter `{"sessionInfo.busUnitId": "apbyfj9d"}`.

## MCP calls run after human go-ahead

- `synamedia-mcp-hub-lightstep_lightstep-eu_list_services` on `mcs-go-prod-iye9omdf-eu` (South Africa, dedicated, no filter) succeeded and returned 125 real services, including generic MTN GO-platform
  services such as `households-api`, `go-mdrmfe`, and `ctap`. This confirmed the project is live and populated.
- `synamedia-mcp-hub-lightstep_lightstep-eu_query_spans` on `mcs-go-prod-mtn-1-eu`, filtered by `sessionInfo.busUnitId == "apbyfj9d"` over `2026-09-30T08:00:00Z` to `2026-09-30T17:00:00Z`, returned
  507 matching spans.
- A stored trace was then pulled for matched span `3098282762723983594` (`start_time 2026-09-30T12:04:00Z`). Every span carried `sessionInfo.busUnitId: apbyfj9d` and
  `sessionInfo.x-synamedia-businessunitid: apbyfj9d`; the request `clientToken` embedded `bu:apbyfj9d!ti:apbyfj9d`; the reporter-level tag remained `syna.tenant: mtn-1`, matching the expected
  shared-project model where the project-wide tag is infra-level and the per-request bus-unit id does the opco disambiguation. Services seen in-trace included `ctap`, `channelLineup`, and
  `vodDiscovery`, consistent with real production Android TV traffic.

## Human correctness judgment

- Human confirmed the shared-project result visibly corresponds to the expected opco (Ghana), not Zambia or South Africa.

## Tool-usage gotcha

- A narrow service+time-window filter combined with `sessionInfo.busUnitId == "<go_id>"` produced empty results because that attribute is not present on every service's spans. The successful pattern
  was to keep the `busUnitId` filter but widen the query to a project-wide, multi-hour window first, then inspect a matched trace. This is worth preserving for later CLI usage/docs so a correct
  shared-project lookup is not mistaken for "no traffic."

## Status

TR-1 passes: the resolution logic matched real MCP results for both a dedicated project (South Africa) and a shared project (Ghana), and the human reviewer explicitly confirmed opco correctness.
