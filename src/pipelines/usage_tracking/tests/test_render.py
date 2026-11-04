"""Tests for the Markdown renderer (no network)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.lib.report_render.protocols import ReportRenderer
from src.pipelines.usage_tracking.athena_source import DeviceSeen, ErrorRow, SessionRow
from src.pipelines.usage_tracking.lightstep_source import RequestRow
from src.pipelines.usage_tracking.merge import build_household_day
from src.pipelines.usage_tracking.render import MarkdownTableRenderer, render_report
from src.pipelines.usage_tracking.roster import Household, Member
from src.pipelines.usage_tracking.rules import apply_rules

DAY = date(2026, 11, 2)
HHID = "22ZVg5IOnUplWxLRa_VVWbs4mE7H41Pp4pInR4UZtqnoiPgBjIcz"
DEV_A, DEV_B, DEV_NEW = "1f1a0cca3e643b1d9058", "2b27dfd73cc805ca2cb2", "9999aaaabbbbccccdddd"
GOLDEN = Path(__file__).parent / "data" / "golden_report.md"
HOUSEHOLD = Household(hhid=HHID, label="Team A", tenant="ZA", track=True, members=(Member("Sai", DEV_A), Member("Fayaz", DEV_B)), phone="1")


def _session(sid: str, dev: str, start: str, end: str, outcome: str, content: str) -> SessionRow:
    return SessionRow(sid, HHID, dev, content, "", outcome, start, end)


def _day_model(sessions: list[SessionRow], errors: list[ErrorRow], requests: list[RequestRow], seen: list[DeviceSeen]):
    return apply_rules(build_household_day(HOUSEHOLD, DAY, sessions, seen, errors, requests))


def test_render_matches_golden_report():
    sessions = [
        _session("abr-vod-1", DEV_A, "2026-11-02 19:19:06.402", "2026-11-02 19:43:32.870", "DESTROY", "Family Feud South Africa"),
        _session("abr-vod-2", DEV_A, "2026-11-02 20:00:00.000", "2026-11-02 20:05:00.000", "PLAYER_ERROR", "True to the Game"),
        _session("abr-vod-0", DEV_B, "2026-10-31 08:00:00.000", "2026-10-31 08:10:00.000", "DESTROY", "Bluey"),
    ]
    errors = [ErrorRow("abr-vod-2", "6007", "Test device | not allowed", "12", "2026-11-02 20:04:00")]
    requests = [RequestRow("abr-vod-1", HHID, DEV_A, "trace-aaa", 5), RequestRow("abr-vod-2", HHID, DEV_A, "trace-bbb", 3), RequestRow("abr-vod-2", HHID, DEV_A, "trace-ccc", 1)]
    seen = [DeviceSeen(HHID, DEV_NEW, 2, "2026-11-02 21:00:00")]
    report = render_report("ZA", DAY, [_day_model(sessions, errors, requests, seen)])
    assert report == GOLDEN.read_text(encoding="utf-8")
    assert all(len(line) <= 200 for line in report.splitlines() if not line.startswith("|"))


def test_render_no_activity_day():
    report = render_report("ZA", DAY, [_day_model([], [], [], [])])
    assert "0 active, 0 sessions, 0 errors" in report
    assert "## Anomalies" in report and "## 7-day trend" in report
    assert report.count("| no |") == 2
    assert " - sessions" not in report


def test_table_renderer_satisfies_protocol_and_escapes_pipes():
    renderer = MarkdownTableRenderer()
    assert isinstance(renderer, ReportRenderer)
    assert "a\\|b" in renderer.render([{"x": "a|b"}])
    assert renderer.render([]) == ""
