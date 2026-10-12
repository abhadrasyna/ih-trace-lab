#!/usr/bin/env python3
"""Summarise HAR timing phases for DASH MPD manifests and audio/video segments.

Reads only URL path, status, size and timings from the HAR; headers, cookies and bodies are never read or printed.

Usage::

    python investigations/inc-latency-shaka-1xxx/scripts/analyze_har_latency.py --har <file.har> --out <report.md>
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.lib.logging.bootstrap import init_logging

PHASES = ("blocked", "dns", "connect", "ssl", "send", "wait", "receive")
KINDS = ("mpd", "video_segment", "audio_segment", "unclassified_segment", "init_segment")
SEGMENT_EXTENSIONS = (".m4f", ".m4s", ".ts", ".cmfv", ".cmfa")


class HarLatencyError(ValueError):
    """Raised when the HAR document does not have the expected shape."""


def classify(url: str) -> str | None:
    """Return the request kind for a URL, or None when it is not MPD/segment traffic."""
    path = urlparse(url).path.lower()
    name = path.rsplit("/", 1)[-1]
    if path.endswith(".mpd"):
        return "mpd"
    if name.startswith("init-") and path.endswith((".mp4", ".m4s")):
        return "init_segment"
    if path.endswith(SEGMENT_EXTENSIONS):
        if "audio" in name:
            return "audio_segment"
        if "video" in name:
            return "video_segment"
        return "unclassified_segment"
    return None


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile; values must be non-empty."""
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * pct // 100))
    return ordered[int(rank) - 1]


def load_samples(document: object) -> list[dict]:
    """Extract one sample per MPD/segment entry from a parsed HAR document."""
    log = document.get("log") if isinstance(document, dict) else None
    entries = log.get("entries") if isinstance(log, dict) else None
    if not isinstance(entries, list):
        raise HarLatencyError("HAR is missing log.entries")
    samples = []
    for index, entry in enumerate(entries):
        url = entry["request"]["url"]
        kind = classify(url)
        if kind is None:
            continue
        timings = entry.get("timings") or {}
        parsed = urlparse(url)
        samples.append(
            {
                "index": index,
                "kind": kind,
                "host": parsed.netloc,
                "name": parsed.path.rsplit("/", 1)[-1],
                "path": parsed.path,
                "status": entry["response"]["status"],
                "started": entry.get("startedDateTime", ""),
                "total_ms": float(entry.get("time", 0)),
                "bytes": max(int(entry["response"].get("content", {}).get("size", 0) or 0), 0),
                "phases": {p: max(float(timings.get(p, 0) or 0), 0.0) for p in PHASES},
            }
        )
    return samples


def summarise_kind(samples: list[dict]) -> dict:
    """Per-phase and total stats for one kind of request."""
    stats = {}
    for label, getter in [("total", lambda s: s["total_ms"])] + [(p, lambda s, p=p: s["phases"][p]) for p in PHASES]:
        values = [getter(s) for s in samples]
        stats[label] = {
            "p50": statistics.median(values),
            "p90": percentile(values, 90),
            "p95": percentile(values, 95),
            "max": max(values),
        }
    return stats


def throughput_kbps(sample: dict) -> float | None:
    """Download throughput from the receive phase only; None when it cannot be computed."""
    receive = sample["phases"]["receive"]
    if receive < 10 or sample["bytes"] <= 0:
        return None
    return sample["bytes"] * 8 / receive


def find_duplicates(samples: list[dict]) -> dict[str, int]:
    """Count requests per (kind, host, path) that were fetched more than once."""
    counts: dict[str, int] = {}
    for s in samples:
        key = f'{s["kind"]}:{s["host"]}{s["path"]}'
        counts[key] = counts.get(key, 0) + 1
    return {k: v for k, v in counts.items() if v > 1}


def render_report(samples: list[dict], har_name: str, slowest: int = 10) -> str:
    """Render the markdown report."""
    lines = [f"# HAR latency: MPD and segments — `{har_name}`", ""]
    lines.append(f"{len(samples)} MPD/segment requests analysed (times in ms; HAR `time`/`timings`).")
    lines.append("")
    for kind in KINDS:
        group = [s for s in samples if s["kind"] == kind]
        if not group:
            continue
        stats = summarise_kind(group)
        statuses: dict[int, int] = {}
        for s in group:
            statuses[s["status"]] = statuses.get(s["status"], 0) + 1
        lines += [f"## {kind} (n={len(group)}, status {dict(sorted(statuses.items()))})", ""]
        lines += ["| phase | p50 | p90 | p95 | max |", "|---|---|---|---|---|"]
        for label in ("total", *PHASES):
            v = stats[label]
            lines.append(f'| {label} | {v["p50"]:.0f} | {v["p90"]:.0f} | {v["p95"]:.0f} | {v["max"]:.0f} |')
        rates = [r for r in (throughput_kbps(s) for s in group) if r is not None]
        if rates:
            lines += ["", f"Receive-phase throughput: median {statistics.median(rates):.0f} kbps, min {min(rates):.0f} kbps."]
        lines.append("")
    lines += [f"## Slowest {slowest} requests by total time", ""]
    lines += ["| kind | name | status | total | wait (TTFB) | receive | bytes | started |", "|---|---|---|---|---|---|---|---|"]
    for s in sorted(samples, key=lambda s: s["total_ms"], reverse=True)[:slowest]:
        lines.append(
            f'| {s["kind"]} | {s["name"]} | {s["status"]} | {s["total_ms"]:.0f} | {s["phases"]["wait"]:.0f} '
            f'| {s["phases"]["receive"]:.0f} | {s["bytes"]} | {s["started"]} |'
        )
    dupes = find_duplicates(samples)
    if dupes:
        lines += ["", f"## Repeated requests ({len(dupes)} URLs fetched more than once)", ""]
        lines += [f"- `{k}` ×{v}" for k, v in sorted(dupes.items())]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    init_logging("analyze-har-latency")
    logger = logging.getLogger("investigations.inc_latency_shaka_1xxx.analyze_har_latency")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--har", type=Path, required=True, help="Input HAR file")
    parser.add_argument("--out", type=Path, required=True, help="Markdown report path")
    parser.add_argument("--slowest", type=int, default=10, help="Rows in the slowest-requests table")
    args = parser.parse_args()
    document = json.loads(args.har.read_text(encoding="utf-8-sig"))
    samples = load_samples(document)
    if not samples:
        raise HarLatencyError("No MPD or segment requests found in the HAR")
    unclassified = sum(1 for s in samples if s["kind"] == "unclassified_segment")
    if unclassified:
        logger.warning("%d segment requests have no audio/video in the file name; see unclassified_segment", unclassified)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_report(samples, args.har.name, args.slowest), encoding="utf-8")
    logger.info("Wrote %s (%d samples)", args.out, len(samples))


if __name__ == "__main__":
    main()
