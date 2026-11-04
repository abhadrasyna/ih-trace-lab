"""Tests for the daily usage report CLI (fake sources, temp directory, no network)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.pipelines.usage_tracking.athena_source import DeviceSeen, ErrorRow, SessionRow
from src.pipelines.usage_tracking.errors import AthenaSourceError
from src.pipelines.usage_tracking.lightstep_source import RequestRow
from src.pipelines.usage_tracking.scripts.run_daily_usage_report import Wiring, main

DAY = date(2026, 11, 2)
TODAY = date(2026, 11, 4)

ROSTER = """
households:
  - hhid: HH-TRACKED
    label: team A
    tenant: ZA
    track: true
    phone: "605209478"
    members:
      - name: Sai
        device_id: dev-sai
  - hhid: HH-UNTRACKED
    label: other
    tenant: ZA
    track: false
    members:
      - name: Nobody
        device_id: dev-nobody
"""


class FakeSessions:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.seen_hhids: set[str] = set()

    def fetch_sessions(self, households, day):
        if self.fail:
            raise AthenaSourceError("SSO refresh failed")
        self.seen_hhids |= {h.hhid for h in households}
        if day != DAY:
            return []
        return [SessionRow("s1", "HH-TRACKED", "dev-sai", "Bluey", "", "PLAYER_ERROR", "2026-11-02 10:00:00.000", "2026-11-02 10:30:00.000")]

    def fetch_household_devices(self, household, day):
        return [DeviceSeen("HH-TRACKED", "dev-new", 1, "2026-11-02 12:00:00")]

    def fetch_errors(self, sessions, day):
        return [ErrorRow("s1", "6007", "denied", "5", "2026-11-02 10:20:00")]


class FakeRequests:
    def fetch_requests(self, households, day):
        return [RequestRow("s1", "HH-TRACKED", "dev-sai", "trace-1", 4)]


def _run(tmp_path: Path, sessions: FakeSessions) -> int:
    config = tmp_path / "roster.yaml"
    config.write_text(ROSTER, encoding="utf-8")
    wiring = Wiring(lambda tenant, live, today: sessions, lambda tenant, live: FakeRequests())
    argv = ["--date", str(DAY), "--config", str(config), "--out-dir", str(tmp_path / "reports")]
    return main(argv, wiring=wiring, today=TODAY)


def test_main_writes_report_for_tracked_households(tmp_path):
    assert _run(tmp_path, FakeSessions()) == 0
    report = (tmp_path / "reports" / "ZA" / f"{DAY}.md").read_text(encoding="utf-8")
    assert "Sai" in report and "trace-1" in report and "6007 denied" in report
    assert "new_device" in report and "dev-new" in report


def test_auth_failure_writes_failed_note_and_exits_nonzero(tmp_path):
    assert _run(tmp_path, FakeSessions(fail=True)) == 1
    out = tmp_path / "reports" / "ZA"
    assert "report not generated" in (out / f"{DAY}.FAILED.txt").read_text(encoding="utf-8")
    assert not (out / f"{DAY}.md").exists()


def test_untracked_household_not_queried(tmp_path):
    sessions = FakeSessions()
    _run(tmp_path, sessions)
    assert sessions.seen_hhids == {"HH-TRACKED"}


def test_successful_rerun_removes_stale_failed_note(tmp_path):
    _run(tmp_path, FakeSessions(fail=True))
    assert _run(tmp_path, FakeSessions()) == 0
    assert not (tmp_path / "reports" / "ZA" / f"{DAY}.FAILED.txt").exists()


def test_failed_rerun_removes_stale_report(tmp_path):
    assert _run(tmp_path, FakeSessions()) == 0
    assert _run(tmp_path, FakeSessions(fail=True)) == 1
    out = tmp_path / "reports" / "ZA"
    assert (out / f"{DAY}.FAILED.txt").exists() and not (out / f"{DAY}.md").exists()


def test_unexpected_error_is_contained_per_tenant(tmp_path):
    class Boom(FakeSessions):
        def fetch_sessions(self, households, day):
            raise RuntimeError("boom")

    assert _run(tmp_path, Boom()) == 1
    assert "boom" in (tmp_path / "reports" / "ZA" / f"{DAY}.FAILED.txt").read_text(encoding="utf-8")


def test_roster_note_removed_once_roster_loads(tmp_path):
    out = tmp_path / "reports"
    main(["--date", str(DAY), "--config", str(tmp_path / "nope.yaml"), "--out-dir", str(out)], wiring=Wiring(None, None), today=TODAY)
    assert (out / f"{DAY}.FAILED.txt").exists()
    assert _run(tmp_path, FakeSessions()) == 0
    assert not (out / f"{DAY}.FAILED.txt").exists()


def test_default_out_dir_is_repo_reports_usage():
    from src.pipelines.usage_tracking.scripts.run_daily_usage_report import DEFAULT_OUT_DIR

    assert DEFAULT_OUT_DIR.parts[-3:] == ("output", "reports", "usage")
    assert (DEFAULT_OUT_DIR.parents[2] / "config" / "tenants.yaml").is_file()


def test_missing_roster_exits_nonzero(tmp_path):
    out = tmp_path / "reports"
    assert main(["--date", str(DAY), "--config", str(tmp_path / "nope.yaml"), "--out-dir", str(out)], wiring=Wiring(None, None), today=TODAY) == 1
    assert "report not generated" in (out / f"{DAY}.FAILED.txt").read_text(encoding="utf-8")
