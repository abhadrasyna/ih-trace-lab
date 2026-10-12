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
- The SSAI MPD answered 200 in 6.2 s, then a 302 in 2.7 s, then the CDN MPD took 3.5 s, so the manifest path alone adds up to several seconds.
- All requests start within about 3 ms of each other (09:56:35.787–.791), which points to contention or queueing rather than per-request origin latency.

## Not yet determined

- Whether the 5–10 s wait is a cold CDN cache (origin pull), a throttled capture network, or the player requesting every segment at once. The script does not read headers, so CDN cache status or Age
  is unchecked.
- Next steps: check the CDN cache-status and Age headers in the HAR, and cross-check the same window in Lightstep or Athena.
