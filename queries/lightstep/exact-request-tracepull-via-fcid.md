# Exact request trace-pull via FCID (client-send → server-receive → server-respond → client-receive)

- Purpose: the aggregate latency queries above show *whether* a route is slow overall, but not *why* one specific request was slow. To pin down exactly where time is spent for one HAR-captured
  request, pull its real distributed trace using the `flow_context` (FCID) value from that request's **response headers** (not a query param — confirmed present on `ctap` responses even when not
  directly queryable as a span tag on `sm-vod`/`households-*`, see "Near-universal but inconsistent shape" above).
- Tool: `query_spans`
- Save exports as: —
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `Exact request trace-pull via FCID (client-send → server-receive → server-respond → client-receive)`

```
uql_filter: FCID == "{{fcid_from_har_response_header}}"
   oldest_time / youngest_time: narrow window around the HAR request's timestamp
```
