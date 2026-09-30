# Reference diagram — vod-playback-timing-probe

This folder's migration value is its end-to-end playback probe chain and its duplicated DASH/MPD parsing logic, not a raw internal-import graph.

## CLI chain

```mermaid
flowchart LR
    A["populate_auth_from_curl.py<br/>or populate_auth_from_har.py"] --> B["populate_ctap_auth_from_har.py"]
    B --> C["discover_content_ids.py<br/>or extract_content_ids_from_har.py"]
    C --> D["extract_flow_from_har.py"]
    D --> E["fill_license_step_from_har.py"]
    E --> F["run_playback_probe.py<br/>or run_full_flow.py"]
    F --> G["generate_timing_report.py<br/>or compare_har_vs_probe.py"]
```

## DASH/MPD convergence

```mermaid
flowchart LR
    PROBE["vod-playback-timing-probe<br/>scripts/playback_probe/mpd_parser.py"] --> MPD["src/lib/mpd/<br/>shared DASH / MPD parser"]
    ROOT["root investigations<br/>scripts/generate_drm_flow_report.py"] --> MPD
```

## Convergence target

- Per GAP-1, this project targets `src/tools/vod-playback-timing-probe/`.
- Its playback-session correlation, flow-template extraction, and live probe orchestration stay local to that tool.
- Its DASH/manifest parsing does **not** stay local: `playback_probe/mpd_parser.py` and root `investigations/scripts/generate_drm_flow_report.py` are the two real consumers that justify the promoted
  `src/lib/mpd/` module.
- That shared `mpd` module is the Tier-3 blocker for `vod-playback-timing-probe-tool-migration`; this diagram exists to make that dependency visible before the actual port starts.
