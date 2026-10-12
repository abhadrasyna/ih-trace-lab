"""Tests for analyze_har_latency (offline, synthetic HAR only)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_har_latency.py"
spec = importlib.util.spec_from_file_location("analyze_har_latency", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["analyze_har_latency"] = mod
spec.loader.exec_module(mod)


def _entry(url: str, total: float, wait: float, receive: float, size: int = 1000, status: int = 200) -> dict:
    return {
        "startedDateTime": "2026-10-12T09:56:35.789Z",
        "time": total,
        "request": {"url": url},
        "response": {"status": status, "content": {"size": size}},
        "timings": {"blocked": 1, "dns": -1, "connect": -1, "ssl": -1, "send": 0, "wait": wait, "receive": receive},
    }


def _har() -> dict:
    base = "https://cdn.example.com/vode/x/"
    return {
        "log": {
            "entries": [
                _entry(base + "a.mpd?token=secret", 300, 250, 5),
                _entry(base + "0/Video1-1.m4f", 9000, 8000, 800, size=100000),
                _entry(base + "0/Video1-1.m4f", 9000, 8000, 800, size=100000),
                _entry(base + "0/Audio1-1.m4f", 100, 90, 5),
                _entry(base + "0/init-Video1.mp4", 50, 40, 5),
                _entry("https://cdn.example.com/app.js", 10, 5, 1),
            ]
        }
    }


@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("https://h/a/b.mpd?x=1", "mpd"),
        ("https://h/0/Video1-5.m4f", "video_segment"),
        ("https://h/0/Audio1-5.m4f", "audio_segment"),
        ("https://h/0/init-Video1.mp4", "init_segment"),
        ("https://h/720p/123.m4s", "unclassified_segment"),
        ("https://h/app.js", None),
    ],
)
def test_classify(url: str, kind: str | None) -> None:
    assert mod.classify(url) == kind


def test_load_samples_filters_non_media() -> None:
    samples = mod.load_samples(_har())
    assert len(samples) == 5
    assert {s["kind"] for s in samples} == {"mpd", "video_segment", "audio_segment", "init_segment"}
    assert all(p >= 0 for s in samples for p in s["phases"].values())


def test_report_stats_duplicates_and_no_query_string() -> None:
    report = mod.render_report(mod.load_samples(_har()), "t.har")
    assert "video_segment (n=2" in report
    assert "Repeated requests" in report
    assert "secret" not in report


def test_same_filename_in_different_folders_is_not_a_repeat() -> None:
    base = "https://cdn.example.com/vode/x/"
    har = {"log": {"entries": [_entry(base + "0/Video1-1.m4f", 10, 5, 5), _entry(base + "1/Video1-1.m4f", 10, 5, 5)]}}
    assert mod.find_duplicates(mod.load_samples(har)) == {}


def test_percentile_and_throughput() -> None:
    assert mod.percentile([1, 2, 3, 4], 90) == 4
    sample = {"bytes": 1000, "phases": {"receive": 80.0}}
    assert mod.throughput_kbps(sample) == 100.0
    assert mod.throughput_kbps({"bytes": 0, "phases": {"receive": 80.0}}) is None
    assert mod.throughput_kbps({"bytes": 1000, "phases": {"receive": 1.0}}) is None


def test_load_samples_rejects_bad_document() -> None:
    with pytest.raises(mod.HarLatencyError):
        mod.load_samples({"log": {}})
