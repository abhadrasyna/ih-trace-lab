#!/usr/bin/env python3
"""
Correlates the CDN team's raw log export (cdnReport/results_sa_*) against
our own output/position_report_DDMMYYYY.csv by IP address + time window,
and classifies each session's likely CDN/network/origin health.

Background: the CDN team's export is a series of blocks, one per (IP,
sessionId) we asked them to check:

    <ip> <window_start_epoch> <window_end_epoch>
    timestamp    stms    ttfb    ttms    sssc    pssc    crc    bytes    url
    <rows...>

The window is always exactly `session start_time - 5 min` to
`start_time + 5 min` — confirmed exact match against our data. See
LEGEND.md ("CDN log fields") for full field semantics and the
classification logic used below (cache hit vs origin fetch, TTFB/ttms,
ERR_CLIENT_ABORT before-data vs mid-transfer, "never reached CDN").

IMPORTANT -- content-aware matching (added 17 Jul 2026, fixing a false-
positive bug): a single (IP, window) block can contain requests for
*several different concurrent/adjacent sessions* on the same shared IP
(dense-traffic IPs, e.g. a household/test-rig replaying content). The old
version classified using ALL rows in the block, so an ERR_CLIENT_ABORT
belonging to a neighbouring session could get misattributed to the session
actually being matched (confirmed for `abr-vod-0bc3ef5f-...` on 10072026 --
see docs/STATUS.md). There is no direct join key between our `contentId`
and the CDN's `vode/<uuid>/` path, so instead we anchor each session to the
nearest `second_screen.mpd` (manifest) request timestamp in the block
(manifest requests reliably land within ~1s of the real session start) and
only count rows between that manifest and the *next* manifest event in the
block (any content UUID) as belonging to this session. Blocks with only one
distinct content UUID need no disambiguation and are handled exactly as
before. See `content_uuid`/`content_match_method` output columns.

Usage:
    python3 correlate_cdn_ips.py --date DDMMYYYY [--cdn-file ../cdnReport/NAME]
                                  [--position-report ../output/position_report_DDMMYYYY.csv]
                                  [--out ../output/cdn_correlation_DDMMYYYY.csv]
                                  [--escalation-out ../output/mtn_escalation_ips_DDMMYYYY.csv]

Also writes an `mtn_escalation` yes/no column per session (see
MTN_ESCALATION_HINTS below) and a separate MTN-escalation IP list CSV
listing just the sessions/IPs that qualify as evidence per docs/STATUS.md
("MTN network-team escalation criteria").
"""
import argparse
from lib import csv_io_compat as csv
import re
import sys
from datetime import datetime, timezone

IP_LINE_RE = re.compile(r'^(\d{1,3}(?:\.\d{1,3}){3})\s+(\d+)\s+(\d+)\s*$')
# vode (DRM-encrypted) or vodc (clear) delivery path -- both seen in real
# CDN log exports (e.g. results_sa_20260709 has both); see
# scripts/merge_ctap_smvod_csv.py and docs/STATUS.md 17 Jul 2026 for the
# vodc case found via session abr-vod-a1082ec1-... on 14072026.
CONTENT_UUID_RE = re.compile(r'/vod[a-z]/([a-f0-9-]+)/')
MANIFEST_MARKER = 'second_screen.mpd'
# Max seconds between a session's own start_time and the nearest manifest
# request in its block for us to trust the manifest as that session's
# anchor (see module docstring). Manifest requests observed within
# ~0.2-0.8s of real session start across every sample checked so far.
MANIFEST_ANCHOR_TOLERANCE_S = 10.0


def extract_content_uuid(url):
    m = CONTENT_UUID_RE.search(url)
    return m.group(1) if m else None


def parse_row_ts(ts_str):
    return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()


def parse_cdn_blocks(cdn_file):
    """Parse the CDN team's export into a list of {ip, wstart, wend, rows}."""
    blocks = []
    cur = None
    with open(cdn_file, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            m = IP_LINE_RE.match(line)
            if m:
                if cur:
                    blocks.append(cur)
                cur = {"ip": m.group(1), "wstart": int(m.group(2)), "wend": int(m.group(3)), "rows": []}
                continue
            if line.startswith("timestamp\t") or not line.strip():
                continue
            if cur is not None:
                parts = line.split('\t')
                if len(parts) >= 9:
                    cur["rows"].append(parts)
    if cur:
        blocks.append(cur)
    return blocks


def parse_sessions(position_report):
    """Parse output/position_report_DDMMYYYY.csv, adding a start_epoch field."""
    sessions = []
    with open(position_report, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ts = (row.get('start_time') or '').replace(' UTC', '').strip()
            if not ts or not row.get('sessionId'):
                continue  # skip blank/trailing rows
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
            sessions.append({**row, "start_epoch": dt.timestamp()})
    return sessions


def classify_row(row):
    """Per-row classification: (is_cache_hit, is_origin_fetch, abort_kind)."""
    # row = [timestamp, stms, ttfb, ttms, sssc, pssc, crc, bytes, url]
    sssc = row[4].strip()
    crc = row[6].strip()
    nbytes = int(row[7]) if row[7].strip().isdigit() else 0
    is_cache_hit = (sssc in ('', '0')) and crc in ('TCP_HIT', 'TCP_MEM_HIT')
    is_origin_fetch = sssc not in ('', '0')
    abort_kind = None
    if crc == 'ERR_CLIENT_ABORT':
        abort_kind = 'mid_transfer' if nbytes > 0 else 'before_data'
    return is_cache_hit, is_origin_fetch, abort_kind


def root_cause_hint(request_count, abort_before, abort_mid, origin_fetch_count, max_ttfb,
                     manifest_only=False):
    """Root-cause hint per the CDN team's (Miltos Margaronis) framework -- see LEGEND.md."""
    if manifest_only:
        # Manifest was fetched (so the request DID reach the CDN) but the
        # session never went on to request a single media segment -- a
        # player/app-side stall (DRM license, decoder init, etc.), not a
        # network/CDN issue. Added 17 Jul 2026 alongside content-aware
        # matching; see abr-vod-0bc3ef5f-... in docs/STATUS.md.
        return "manifest_only_no_segment_requests (client never requested media after manifest)"
    if request_count == 0:
        return "network_issue_before_cdn (request never reached CDN in window)"
    if abort_mid > 0:
        return "client_network_disconnect_suspected (mid-transfer ERR_CLIENT_ABORT)"
    if origin_fetch_count > 0 and max_ttfb > 2000:
        return "origin_latency_suspected (slow origin fetch, high ttfb)"
    if abort_before > 0:
        return "benign_client_abort_only (aborted before data started)"
    return "cdn_healthy_no_red_flags"


# root_cause_hint prefixes that qualify as MTN network-team escalation evidence
# -- see docs/STATUS.md ("MTN network-team escalation criteria") and
# LEGEND.md ("CDN log fields") for the trigger/rationale. Deliberately does
# NOT include manifest_only_no_segment_requests -- that's an app/player-side
# symptom, not network evidence.
MTN_ESCALATION_HINTS = ("network_issue_before_cdn", "client_network_disconnect_suspected")


def mtn_escalation_flag(hint):
    return "yes" if hint.startswith(MTN_ESCALATION_HINTS) else "no"


def compute_row_metrics(rows):
    """Aggregate cache/origin/abort/ttfb/ttms stats over a set of raw CDN rows."""
    total_bytes = sum(int(r[7]) for r in rows if r[7].strip().isdigit())
    crcs = {}
    cache_hit_count = origin_fetch_count = abort_before = abort_mid = 0
    for r in rows:
        crcs[r[6].strip()] = crcs.get(r[6].strip(), 0) + 1
        is_hit, is_origin, abort_kind = classify_row(r)
        cache_hit_count += is_hit
        origin_fetch_count += is_origin
        if abort_kind == 'before_data':
            abort_before += 1
        elif abort_kind == 'mid_transfer':
            abort_mid += 1
    max_ttfb = max((int(r[2]) for r in rows if r[2].strip().lstrip('-').isdigit()), default=0)
    max_ttms = max((int(r[3]) for r in rows if r[3].strip().lstrip('-').isdigit()), default=0)
    return {
        "total_bytes": total_bytes, "crcs": crcs,
        "cache_hit_count": cache_hit_count, "origin_fetch_count": origin_fetch_count,
        "abort_before": abort_before, "abort_mid": abort_mid,
        "max_ttfb": max_ttfb, "max_ttms": max_ttms,
    }


def isolate_session_rows(rows, session_start_epoch):
    """
    Content-aware disambiguation within a shared (IP, window) block.

    Returns (isolated_rows, content_uuid, match_method):
      - match_method == 'single_stream_no_ambiguity': block has only one
        distinct content UUID -- no disambiguation needed, all rows used.
      - match_method == 'manifest_anchor_matched': multiple concurrent
        streams present, but a `second_screen.mpd` request within
        MANIFEST_ANCHOR_TOLERANCE_S of the session's own start_time was
        found and used as an anchor; only rows for that UUID, between the
        anchor and the next manifest event (any UUID) in the block, are
        returned.
      - match_method == 'no_manifest_anchor_multi_stream_unconfirmed':
        multiple streams present and no manifest anchor could be matched
        within tolerance -- cannot confidently isolate this session's own
        traffic, so the full (unfiltered) block is returned but flagged as
        unconfirmed (caller should not treat this as strong evidence).
    """
    tagged = []
    for r in rows:
        uuid = extract_content_uuid(r[8])
        ts = None
        try:
            ts = parse_row_ts(r[0])
        except ValueError:
            pass
        tagged.append((uuid, ts, r))

    distinct_uuids = {u for u, _, _ in tagged if u}
    if len(distinct_uuids) <= 1:
        return rows, (next(iter(distinct_uuids), None)), 'single_stream_no_ambiguity'

    manifest_events = sorted(
        {(ts, uuid) for uuid, ts, r in tagged if ts is not None and uuid and MANIFEST_MARKER in r[8]}
    )
    if not manifest_events:
        return rows, None, 'no_manifest_anchor_multi_stream_unconfirmed'

    anchor_ts, anchor_uuid = min(manifest_events, key=lambda e: abs(e[0] - session_start_epoch))
    if abs(anchor_ts - session_start_epoch) > MANIFEST_ANCHOR_TOLERANCE_S:
        return rows, None, 'no_manifest_anchor_multi_stream_unconfirmed'

    later_manifests = sorted(ts for ts, _ in manifest_events if ts > anchor_ts + 1e-6)
    segment_end = later_manifests[0] if later_manifests else float('inf')

    isolated = [r for uuid, ts, r in tagged
                if uuid == anchor_uuid and ts is not None and anchor_ts - 1e-6 <= ts < segment_end]
    return isolated, anchor_uuid, 'manifest_anchor_matched'


def match_ip_group(blocks_with_idx, sessions_with_idx, tolerance=2.0):
    """
    Optimal (not greedy) matching of one IP's blocks to that IP's sessions,
    preserving chronological order on both sides (blocks are generated by
    the CDN team's automation in the same order sessions were submitted).

    Needed because dense bursts -- many sessions on the same IP seconds
    apart -- can make a naive "closest available block per session" greedy
    match leave a block unassigned even when a perfect pairing exists (seen
    in results_sa_20260709, IP 196.210.20.122, 12 sessions/12 blocks all
    within ~1s of each other).

    Solved via sequence-alignment-style DP: both sides sorted by time,
    matches must be non-crossing (monotonic), cost = time diff if within
    `tolerance`, else that pairing is disallowed. Equivalent to weighted
    edit-distance with only substitutions/skips (no true "insert" cost
    beyond skipping an element).
    """
    blocks_with_idx = sorted(blocks_with_idx, key=lambda x: x[1])
    sessions_with_idx = sorted(sessions_with_idx, key=lambda x: x[1])
    n, m = len(blocks_with_idx), len(sessions_with_idx)
    INF = float('inf')
    # A match must always beat any number of skips, so first maximize match
    # count, then minimize total time diff among equal-count solutions. Give
    # every match a large fixed bonus (-BIG) plus its (small, < tolerance)
    # diff, and every skip cost 0 -- summing costs then naturally prefers
    # more matches first, smallest diffs second.
    BIG = 1_000_000.0
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0]
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1]
    for i in range(1, n + 1):
        _, bcenter = blocks_with_idx[i - 1]
        for j in range(1, m + 1):
            _, sepoch = sessions_with_idx[j - 1]
            diff = abs(bcenter - sepoch)
            match_cost = dp[i - 1][j - 1] + diff - BIG if diff < tolerance else INF
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], match_cost)

    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        _, bcenter = blocks_with_idx[i - 1]
        _, sepoch = sessions_with_idx[j - 1]
        diff = abs(bcenter - sepoch)
        match_cost = dp[i - 1][j - 1] + diff - BIG if diff < tolerance else INF
        if dp[i][j] == match_cost and match_cost != INF:
            pairs.append((blocks_with_idx[i - 1][0], sessions_with_idx[j - 1][0]))
            i, j = i - 1, j - 1
        elif dp[i][j] == dp[i - 1][j]:
            i -= 1
        else:
            j -= 1
    return pairs


def correlate(cdn_file, position_report, out_file, escalation_out_file=None):
    blocks = parse_cdn_blocks(cdn_file)
    print(f"Parsed {len(blocks)} CDN blocks", file=sys.stderr)

    sessions = parse_sessions(position_report)
    print(f"Parsed {len(sessions)} sessions", file=sys.stderr)

    # Group by IP, then run the order-preserving optimal match per IP
    # (fixes the dense-burst matching bug -- see match_ip_group docstring).
    session_to_block = {}
    ips = {s['session.clientIp'] for s in sessions} | {b['ip'] for b in blocks}
    for ip in ips:
        ip_blocks = [(i, (b['wstart'] + b['wend']) / 2.0) for i, b in enumerate(blocks) if b['ip'] == ip]
        ip_sessions = [(j, s['start_epoch']) for j, s in enumerate(sessions) if s['session.clientIp'] == ip]
        if not ip_blocks or not ip_sessions:
            continue
        for block_idx, session_idx in match_ip_group(ip_blocks, ip_sessions):
            session_to_block[session_idx] = block_idx

    used_blocks = set(session_to_block.values())
    results = []
    for j, s in enumerate(sessions):
        ip = s['session.clientIp']
        best = session_to_block.get(j)

        base = {
            "sessionId": s['sessionId'],
            "clientIp": ip,
            "start_time": s['start_time'],
            "state_sequence": s['state_sequence'],
            "error_codes": s['error_codes'],
        }

        if best is None:
            results.append({
                **base,
                "cdn_window_start": "", "cdn_window_end": "",
                "cdn_request_count": 0, "cdn_total_bytes": 0,
                "cdn_crc_breakdown": "", "cache_hit_count": 0,
                "origin_fetch_count": 0, "abort_before_data_count": 0,
                "abort_mid_transfer_count": 0, "cdn_max_ttfb_ms": 0,
                "cdn_max_ttms_ms": 0, "root_cause_hint": "no_cdn_block_found_for_ip",
                "content_uuid": "", "content_match_method": "",
                "mtn_escalation": "no",
                "match_status": "no_cdn_block_found",
            })
            continue

        b = blocks[best]
        # Content-aware disambiguation -- isolate rows likely to belong to
        # THIS session when the block is shared with concurrent/adjacent
        # streams on the same IP (see isolate_session_rows docstring).
        isolated_rows, content_uuid, match_method = isolate_session_rows(b['rows'], s['start_epoch'])

        if match_method == 'no_manifest_anchor_multi_stream_unconfirmed':
            # Can't confidently isolate this session's own traffic -- report
            # the raw block stats for visibility but don't trust them enough
            # to classify a root cause or escalate.
            m = compute_row_metrics(b['rows'])
            results.append({
                **base,
                "cdn_window_start": datetime.fromtimestamp(b['wstart'], tz=timezone.utc).isoformat(),
                "cdn_window_end": datetime.fromtimestamp(b['wend'], tz=timezone.utc).isoformat(),
                "cdn_request_count": len(b['rows']),
                "cdn_total_bytes": m['total_bytes'],
                "cdn_crc_breakdown": ";".join(f"{k}={v}" for k, v in sorted(m['crcs'].items())),
                "cache_hit_count": m['cache_hit_count'],
                "origin_fetch_count": m['origin_fetch_count'],
                "abort_before_data_count": m['abort_before'],
                "abort_mid_transfer_count": m['abort_mid'],
                "cdn_max_ttfb_ms": m['max_ttfb'],
                "cdn_max_ttms_ms": m['max_ttms'],
                "root_cause_hint": "ambiguous_shared_ip_multiple_streams (cannot isolate this session's own traffic)",
                "content_uuid": "", "content_match_method": match_method,
                "mtn_escalation": "no",
                "match_status": "matched_unconfirmed",
            })
            continue

        manifest_only = (match_method == 'manifest_anchor_matched' and len(isolated_rows) > 0
                          and all(MANIFEST_MARKER in r[8] for r in isolated_rows))
        m = compute_row_metrics(isolated_rows)
        hint = root_cause_hint(len(isolated_rows), m['abort_before'], m['abort_mid'],
                                m['origin_fetch_count'], m['max_ttfb'], manifest_only=manifest_only)

        results.append({
            **base,
            "cdn_window_start": datetime.fromtimestamp(b['wstart'], tz=timezone.utc).isoformat(),
            "cdn_window_end": datetime.fromtimestamp(b['wend'], tz=timezone.utc).isoformat(),
            "cdn_request_count": len(isolated_rows),
            "cdn_total_bytes": m['total_bytes'],
            "cdn_crc_breakdown": ";".join(f"{k}={v}" for k, v in sorted(m['crcs'].items())),
            "cache_hit_count": m['cache_hit_count'],
            "origin_fetch_count": m['origin_fetch_count'],
            "abort_before_data_count": m['abort_before'],
            "abort_mid_transfer_count": m['abort_mid'],
            "cdn_max_ttfb_ms": m['max_ttfb'],
            "cdn_max_ttms_ms": m['max_ttms'],
            "root_cause_hint": hint,
            "content_uuid": content_uuid or "",
            "content_match_method": match_method,
            "mtn_escalation": mtn_escalation_flag(hint),
            "match_status": "matched",
        })

    unmatched_blocks = [b for i, b in enumerate(blocks) if i not in used_blocks]
    print(f"Matched {len(used_blocks)}/{len(blocks)} blocks to sessions; "
          f"{len(unmatched_blocks)} blocks unmatched", file=sys.stderr)
    for b in unmatched_blocks:
        print(f"  unmatched block: ip={b['ip']} window=[{b['wstart']},{b['wend']}] rows={len(b['rows'])}",
              file=sys.stderr)

    fieldnames = list(results[0].keys())
    with open(out_file, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    matched = sum(1 for r in results if r['match_status'] == 'matched')
    print(f"\nWrote {out_file}: {matched}/{len(results)} sessions matched to a CDN block", file=sys.stderr)

    # --- MTN network-team escalation IP list --- see docs/STATUS.md
    # ("MTN network-team escalation criteria") for the trigger/process.
    escalation_rows = [r for r in results if r['mtn_escalation'] == 'yes']
    if escalation_out_file:
        esc_fieldnames = ["clientIp", "sessionId", "start_time", "root_cause_hint",
                          "cdn_window_start", "cdn_window_end", "cdn_request_count",
                          "abort_mid_transfer_count", "error_codes",
                          "content_uuid", "content_match_method"]
        with open(escalation_out_file, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=esc_fieldnames)
            w.writeheader()
            for r in escalation_rows:
                w.writerow({k: r[k] for k in esc_fieldnames})
        unique_ips = sorted({r['clientIp'] for r in escalation_rows})
        print(f"Wrote {escalation_out_file}: {len(escalation_rows)} escalation-candidate "
              f"sessions across {len(unique_ips)} unique IP(s)", file=sys.stderr)
        print("IPs to check with MTN:", file=sys.stderr)
        for ip in unique_ips:
            print(f"  {ip}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', required=True, help='DDMMYYYY, used for default file names')
    ap.add_argument('--cdn-file', help='Path to CDN team export (default: guess from --date)')
    ap.add_argument('--position-report', help='Path to position_report CSV (default: ../output/position_report_<date>.csv)')
    ap.add_argument('--out', help='Output path (default: ../output/cdn_correlation_<date>.csv)')
    ap.add_argument('--escalation-out', help='Output path for the MTN-escalation IP list '
                     '(default: ../output/mtn_escalation_ips_<date>.csv)')
    args = ap.parse_args()

    date = args.date
    yyyymmdd = date[4:8] + date[2:4] + date[0:2]
    cdn_file = args.cdn_file or f"../cdnReport/results_sa_{yyyymmdd}"
    position_report = args.position_report or f"../output/position_report_{date}.csv"
    out_file = args.out or f"../output/cdn_correlation_{date}.csv"
    escalation_out_file = args.escalation_out or f"../output/mtn_escalation_ips_{date}.csv"

    correlate(cdn_file, position_report, out_file, escalation_out_file)


if __name__ == '__main__':
    main()
