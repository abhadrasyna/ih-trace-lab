# HAR latency: MPD and segments — `onetv2.mtn.com_latency.har`

23 MPD/segment requests analysed (times in ms; HAR `time`/`timings`).

## mpd (n=3, status {200: 2, 302: 1})

| phase | p50 | p90 | p95 | max |
|---|---|---|---|---|
| total | 3453 | 6192 | 6192 | 6192 |
| blocked | 2 | 20 | 20 | 20 |
| dns | 0 | 0 | 0 | 0 |
| connect | 0 | 0 | 0 | 0 |
| ssl | 0 | 0 | 0 | 0 |
| send | 0 | 0 | 0 | 0 |
| wait | 2711 | 3898 | 3898 | 3898 |
| receive | 2293 | 2297 | 2297 | 2297 |

Receive-phase throughput: median 429 kbps, min 429 kbps.

## video_segment (n=8, status {200: 8})

| phase | p50 | p90 | p95 | max |
|---|---|---|---|---|
| total | 8547 | 9737 | 9737 | 9737 |
| blocked | 2 | 4 | 4 | 4 |
| dns | 0 | 0 | 0 | 0 |
| connect | 0 | 0 | 0 | 0 |
| ssl | 0 | 0 | 0 | 0 |
| send | 0 | 0 | 0 | 0 |
| wait | 7677 | 8941 | 8941 | 8941 |
| receive | 789 | 950 | 950 | 950 |

Receive-phase throughput: median 1198 kbps, min 1060 kbps.

## audio_segment (n=8, status {200: 8})

| phase | p50 | p90 | p95 | max |
|---|---|---|---|---|
| total | 4177 | 7205 | 7205 | 7205 |
| blocked | 1 | 5 | 5 | 5 |
| dns | 0 | 0 | 0 | 0 |
| connect | 0 | 0 | 0 | 0 |
| ssl | 0 | 0 | 0 | 0 |
| send | 0 | 1 | 1 | 1 |
| wait | 1936 | 5253 | 5253 | 5253 |
| receive | 2047 | 2333 | 2333 | 2333 |

Receive-phase throughput: median 957 kbps, min 845 kbps.

## init_segment (n=4, status {200: 4})

| phase | p50 | p90 | p95 | max |
|---|---|---|---|---|
| total | 5256 | 9741 | 9741 | 9741 |
| blocked | 2 | 5 | 5 | 5 |
| dns | 0 | 0 | 0 | 0 |
| connect | 0 | 0 | 0 | 0 |
| ssl | 0 | 0 | 0 | 0 |
| send | 0 | 1 | 1 | 1 |
| wait | 5252 | 9740 | 9740 | 9740 |
| receive | 1 | 2 | 2 | 2 |

## Slowest 10 requests by total time

| kind | name | status | total | wait (TTFB) | receive | bytes | started |
|---|---|---|---|---|---|---|---|
| init_segment | init-Video1.mp4 | 200 | 9741 | 9740 | 0 | 1456 | 2026-10-12T09:56:35.789Z |
| init_segment | init-Video1.mp4 | 200 | 9738 | 9732 | 2 | 0 | 2026-10-12T09:56:35.789Z |
| video_segment | Video1-1214588.m4f | 200 | 9737 | 8941 | 794 | 126064 | 2026-10-12T09:56:35.789Z |
| video_segment | Video1-1214588.m4f | 200 | 9734 | 8936 | 795 | 0 | 2026-10-12T09:56:35.791Z |
| video_segment | Video1-133508.m4f | 200 | 8941 | 8157 | 783 | 110159 | 2026-10-12T09:56:35.789Z |
| video_segment | Video1-133508.m4f | 200 | 8939 | 8150 | 785 | 0 | 2026-10-12T09:56:35.790Z |
| video_segment | Video1-674048.m4f | 200 | 8156 | 7205 | 950 | 125840 | 2026-10-12T09:56:35.789Z |
| video_segment | Video1-674048.m4f | 200 | 8147 | 7198 | 946 | 0 | 2026-10-12T09:56:35.790Z |
| audio_segment | Audio1-1216388.m4f | 200 | 7205 | 5253 | 1952 | 243912 | 2026-10-12T09:56:35.787Z |
| audio_segment | Audio1-1216388.m4f | 200 | 7198 | 5245 | 1948 | 0 | 2026-10-12T09:56:35.788Z |

## Repeated requests (11 URLs fetched more than once)

- `audio_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Audio1-1216388.m4f` ×2
- `audio_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Audio1-129668.m4f` ×2
- `audio_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Audio1-1755908.m4f` ×2
- `audio_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Audio1-674948.m4f` ×2
- `init_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/init-Audio1.mp4` ×2
- `init_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/init-Video1.mp4` ×2
- `mpd:vod-dai-ott-eu2.ssai.iris.synamedia.com/tenant/sun902py/ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/second_screen.mpd` ×2
- `video_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Video1-1214588.m4f` ×2
- `video_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Video1-133508.m4f` ×2
- `video_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Video1-1755128.m4f` ×2
- `video_segment:ng-vod.cdn.yellotv.mtn.com/apbyfj9d/dash-wv-pr/vode/08eeb9d4-742e-52c4-b0f2-f45ae7803ccf/0/Video1-674048.m4f` ×2
