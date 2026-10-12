# HAR latency summary — MPD and segments (INC0256345 & INC0256143)

Source: `data/har/onetv2.mtn.com_latency.har`, captured 2026-10-12 around 09:56 UTC (42 entries, 23 MPD/segment requests). Analysed with `scripts/analyze_har_latency.py`; full phase tables in
`output/har-latency-mpd-segments.md`.

## Latency by request type (seconds)

| What | Host | Requests | Min | Median | Max |
|---|---|---|---|---|---|
| MPD (SSAI 200, SSAI 302, CDN 200) | `vod-dai-ott-eu2.ssai.iris.synamedia.com`, `ng-vod.cdn.yellotv.mtn.com` | 3 | 2.7 | 3.5 | 6.2 |
| Init segments (audio + video) | `ng-vod.cdn.yellotv.mtn.com` | 4 | 0.8 | 5.3 | 9.7 |
| Audio segments | `ng-vod.cdn.yellotv.mtn.com` | 8 | 1.9 | 4.2 | 7.2 |
| Video segments | `ng-vod.cdn.yellotv.mtn.com` | 8 | 2.5 | 8.5 | 9.7 |

Every URL was fetched twice, so there are only 4 unique video and 4 unique audio segments. The median alone is a weak measure on this sample; the min/max range matters more.

## Where the time goes

| Segment type | Wait for first byte (TTFB), median / max | Receive, median / max |
|---|---|---|
| Video | 7.7 s / 8.9 s | 0.8 s / 1.0 s (about 1.2 Mbps) |
| Audio | 1.9 s / 5.3 s | 2.0 s / 2.3 s |
| Init | 5.3 s / 9.7 s | about 0.001 s |

- Video and init segment delay is almost entirely before the first byte, not in transfer.
- DNS, connect and SSL are -1 on every request (connections reused), so connection setup is not the cause.
- The SSAI "200" entry (6.2 s) is the whole redirect chain: the SSAI 302 (2.7 s) plus the CDN MPD fetch (3.5 s). It started at the same instant as the 302, so it is not a separate request.
- All requests start within about 3 ms of each other (09:56:35.787–.791), which points to contention or queueing rather than per-request origin latency.

## Manifest path: how much is Iris (seconds)

HAR request at 09:56:27 UTC, cross-checked against Lightstep project `mcs-iris-production-eu` (EU), tenant `sun902py`.

| Part of the 6.2 s manifest path | Time | Share |
|---|---|---|
| Iris `vod-stitcher` server time (Lightstep root span, 302) | 2.3 | about 38% |
| Rest of the 2.7 s SSAI hop (network, CloudFront, ingress; not measured further) | 0.4 | about 6% |
| CDN MPD fetch, `ng-vod.cdn.yellotv.mtn.com` (1.15 s wait + 2.30 s receive) | 3.45 | about 56% |
| Total (redirect chain) | 6.2 | 100% |

Inside the 2.3 s of Iris:

| Step (in order) | Service / span | Time (s) |
|---|---|---|
| Middleware chain (cors, tenant, consent, URL checks) | `vod-stitcher` | about 0 |
| `manifest_origin`: fetch MPD from the MTN CDN (`tcp.connect` 0.30, `tls.connect` 0.42, rest is wait and transfer) | `vod-stitcher` → `ng-vod.cdn.yellotv.mtn.com` | 2.29 |
| `ad_server` call, which uses `content-inventory` and one `mongodb.find` | `vod-stitcher` → `ott-ad-decision` | 0.011 |
| Respond 302 to the CDN URL | `vod-stitcher` | ends at 2.31 |

About 99% of the Iris time is `manifest_origin` waiting on the same MTN CDN origin; ad decisioning is not the cause. Entry service for the flow: `vod-stitcher` (first service in the trace).

## HAR to Lightstep mapping

- The SSAI 302 response header `fcid` is a W3C traceparent (`00-<trace id>-<span id>-01`) and equals the `ssai.FCID` tag on the `vod-stitcher` span. Its trace ID is the span's `otlp.trace_id`, and its
  span ID is the root span `HTTP GET vod-stitcher`. Search Lightstep with `ssai.FCID == "<fcid>"` or fetch the trace by ID.
- Only the SSAI 302 carries `fcid` (and `rid`, which was not found as a span tag). CDN MPD and segment requests have no Iris correlation header.
- Weaker links: tenant `syna.iris.tenant_id`, the content ID in the URL path, request time, and the query string (the vod-stitcher log line holds the full URL; it contains device and subscriber IDs,
  so do not copy it into docs).
- The SSAI response also passes through CloudFront (`x-cache: Miss from cloudfront`, POP `BLR50-P2`).

## Not yet determined

- Whether the 5–10 s wait on segments is a cold CDN cache (origin pull), a throttled capture network, or the player requesting every segment at once. The script does not read headers, so CDN cache
  status or Age is unchecked, and the segments are not Iris traffic.
- Why `manifest_origin` takes 2.29 s (about 1.6 s beyond tcp/tls) when the browser's own CDN MPD fetch also took 3.45 s: the same origin looks slow for both.
- Next steps: check the CDN cache-status and Age headers in the HAR, and add `fcid` to the script's report.
