# INC0256345 & INC0256143 – latency and Shaka 1xxx errors

## Inputs used

- HAR: `data/har/onetv2.mtn.com_latency.har` (captured 2026-10-12 ~09:56 UTC, 42 entries, 23 MPD/segment); analysed by `scripts/analyze_har_latency.py`, report in `output/har-latency-mpd-segments.md`
- Lightstep: EU, project `mcs-iris-production-eu`, notebook `ww0TBBjh` ("Iris manifest", created 2026-10-12), queries on service `vod-stitcher`, tenant `sun902py`, content
  `08eeb9d4-742e-52c4-b0f2-f45ae7803ccf`; stored trace fetched by span ID
- Athena: not used

## Findings

### HAR: MPD and segment latency (2026-10-12)

- MPD: 3 HAR entries, p50 total 3.5 s, max 6.2 s. The 6.2 s SSAI "200" entry is the redirect chain: the SSAI 302 (2.7 s) plus the CDN MPD fetch (3.5 s), started at the same instant as the 302.
- Iris share of the manifest path: Lightstep shows `vod-stitcher` took about 2.3 s (about 38% of 6.2 s), of which `manifest_origin` (fetching the MPD from `ng-vod.cdn.yellotv.mtn.com`) is 2.29 s and
  `ott-ad-decision` is 0.011 s. About 0.4 s of the 2.7 s hop is outside Iris (CloudFront, network). The CDN fetch is the remaining 3.45 s. Details and the `fcid` HAR-to-trace mapping are in
  `har-latency-summary.md`.
- Video segments: p50 total 8.5 s, max 9.7 s, almost all of it TTFB (wait p50 7.7 s, max 8.9 s). Receive is only about 0.8 s (about 1.2 Mbps).
- Audio segments: p50 total 4.2 s, max 7.2 s, wait p50 1.9 s, receive p50 2.0 s.
- Init segments: wait p50 5.3 s, max 9.7 s, receive about 1 ms, so the delay is before the first byte, not in transfer.
- dns/connect/ssl are -1 (reused connections), so the delay is server/queue wait, not connection setup.
- Every request starts within about 3 ms of the others (09:56:35.787-.791) and every URL appears twice (the second copy has 0 body bytes). That burst of parallel fetches suggests contention or
  queueing rather than per-request origin latency.
- Not yet determined: whether the 5-10 s TTFB is CDN origin pull (cold cache), throttled capture network, or the player requesting all segments at once. Confirming that needs the CDN cache-status/Age
  headers (not read by the script) or a Lightstep/Athena cross-check.
