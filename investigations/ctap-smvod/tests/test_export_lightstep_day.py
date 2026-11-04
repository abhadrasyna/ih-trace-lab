"""Tests for export_lightstep_day.py (CLI wiring with a fake Lightstep transport; no network)."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import load_script

cli = load_script("export_lightstep_day.py")
from scripts.lib import lightstep_export_kinds as kinds_mod  # noqa: E402
from scripts.lib import lightstep_export_runner as runner  # noqa: E402
from scripts.lib.lightstep_csv import build_rows  # noqa: E402
from scripts.lib.lightstep_parallel import SerialJobRunner, ThreadJobRunner  # noqa: E402
from src.lib.logging.context import FcidLogFilter, bind_fcid  # noqa: E402
from src.tenant_registry import TenantRegistry  # noqa: E402

TOKEN = "s3cret-token-value"
DAY = "2026-10-29"
ALL_KINDS = sorted(kinds_mod.KINDS)


class FakeTransport:
    """Answers every call with one series whose labels come from the query's group_by list."""

    def __init__(self, fail_marker: str | None = None) -> None:
        self.fail_marker = fail_marker
        self.calls = 0

    def post(self, url, headers, body, timeout):
        self.calls += 1
        query = json.loads(body)["data"]["attributes"]["query"]
        if self.fail_marker and self.fail_marker in query:
            return 400, b"bad query"
        names = re.search(r"group_by \[(.*?)\]", query, re.DOTALL).group(1)
        labels = [f"{name.strip().strip(chr(34))}=v" for name in names.split(",")]
        series = [{"group-labels": labels, "points": [[1_700_000_000_000, 1]]}]
        return 200, json.dumps({"data": {"attributes": {"series": series}}}).encode()


@pytest.fixture(autouse=True)
def _isolated_parts_root(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "DEFAULT_PARTS_ROOT", tmp_path.with_name(tmp_path.name + "_parts"))


def _run(tmp_path, monkeypatch, *, kinds=ALL_KINDS, transport=None, check=None, force=False, tenant="ZA", workers=1, out=None):
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    monkeypatch.setenv("LIGHTSTEP_API_KEY_US", TOKEN)
    deps = runner.Dependencies(
        transport=transport or FakeTransport(), tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=check or (lambda directory, drm: ("ok", True)), report=runner.print_report,
        job_runner=ThreadJobRunner(workers),
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get(tenant), day=DAY, kinds=kinds, out_dir=out or tmp_path, force=force)
    return runner.run_export(request, deps)


def test_default_date_is_yesterday_utc():
    assert cli.default_date(datetime(2026, 11, 1, 0, 30, tzinfo=timezone.utc)) == "2026-10-31"


def test_all_kinds_written_for_tenant_date(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(f"{DAY}_{kind}.csv" for kind in ALL_KINDS)


def test_one_failed_kind_continues_and_exits_nonzero(tmp_path, monkeypatch):
    code = _run(tmp_path, monkeypatch, transport=FakeTransport(fail_marker="go-mdrmfe"))
    assert code == 1
    assert not (tmp_path / f"{DAY}_mdrmfe.csv").exists()
    assert (tmp_path / f"{DAY}_ctap.csv").exists() and (tmp_path / f"{DAY}_mdrm-lrm.csv").exists()


def test_failed_input_check_exits_nonzero(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, check=lambda directory, drm: ("FAIL smvod-ts coverage", False)) == 1


def test_input_check_runs_on_output_dir(tmp_path, monkeypatch):
    seen: list[Path] = []
    _run(tmp_path, monkeypatch, check=lambda directory, drm: (seen.append(directory), ("ok", True))[1])
    assert seen == [tmp_path]


def test_existing_file_skipped_without_force(tmp_path, monkeypatch):
    (tmp_path / f"{DAY}_ctap.csv").write_text("keep", encoding="utf-8")
    transport = FakeTransport()
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=transport) == 0
    assert (tmp_path / f"{DAY}_ctap.csv").read_text(encoding="utf-8") == "keep" and transport.calls == 0


def test_shared_tenant_with_foreign_busunitid_fails(tmp_path, monkeypatch):
    series = [{"group-labels": ["busUnitId=other"], "points": []}]
    with pytest.raises(runner.TenantSafetyError):
        runner.check_single_tenant(series, kinds_mod.get_kind("smvod"), TenantRegistry().get("ZM"))


def test_log_lines_carry_one_fcid_and_no_token(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    runner.LOGGER.addFilter(FcidLogFilter())
    bind_fcid("export-lightstep-day-test")
    try:
        _run(tmp_path, monkeypatch, kinds=["ctap", "mdrm-lrm"])
    finally:
        runner.LOGGER.filters.clear()
    own = [record for record in caplog.records if record.name == runner.LOGGER.name]
    assert own and {record.fcid for record in own} == {"export-lightstep-day-test"}
    assert TOKEN not in caplog.text
    messages = [record.getMessage() for record in own]
    assert any(m.startswith("part 1/") and "eta_s=" in m and "window=" in m for m in messages)
    assert any(m.startswith("stitching kind=ctap") for m in messages)
    assert any(m.startswith("kind done kind=ctap elapsed=") for m in messages)
    assert any(m.startswith("cleanup tmp=") for m in messages)


def test_main_writes_log_named_by_data_day_and_prunes_old_files(tmp_path, monkeypatch):
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    logs = tmp_path / "logs"
    logs.mkdir()
    old = logs / "export-lightstep-day_2000-01-01.log"
    unrelated = logs / "14102026.txt"
    for path in (old, unrelated):
        path.write_text("x", encoding="utf-8")
    argv = ["--tenant", "ZA", "--date", DAY, "--kinds", "ctap", "--output-dir", str(tmp_path / "out"), "--log-dir", str(logs)]
    try:
        cli.main(argv, FakeTransport(), lambda directory, drm: ("ok", True))
        cli.main(argv, FakeTransport(), lambda directory, drm: ("ok", True))
    finally:
        logging.getLogger().handlers.clear()
    log_file = logs / f"export-lightstep-day_{DAY}.log"
    text = log_file.read_text(encoding="utf-8")
    assert text.count("run start") == 2 and TOKEN not in text
    assert not old.exists() and unrelated.exists()


def test_output_dir_argument_redirects_csvs_and_check(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "init_logging", lambda slug, **kwargs: "fcid")
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    seen: list[Path] = []
    target = tmp_path / "elsewhere"
    argv = ["--tenant", "ZA", "--date", DAY, "--kinds", "ctap", "smvod", "smvod-ts", "--output-dir", str(target)]
    code = cli.main(argv, FakeTransport(), lambda directory, drm: (seen.append(directory), ("ok", True))[1])
    assert code == 0 and seen == [target]
    assert sorted(p.name for p in target.iterdir()) == [f"{DAY}_ctap.csv", f"{DAY}_smvod-ts.csv", f"{DAY}_smvod.csv"]


def test_new_registry_entry_needs_no_cli_change(tmp_path, monkeypatch):
    seen = []

    def builder(series, columns):
        seen.append(len(series))
        return build_rows(series, columns)

    spec = kinds_mod.KindSpec(
        "extra", "lightstep-export-ctap", kinds_mod.GO, "extra", ("http.user_agent", "lightstep.trace_id"),
        row_builder=builder, availability=lambda tenant: "extra is off" if tenant.code == "ZM" else None,
    )
    monkeypatch.setitem(kinds_mod.KINDS, "extra", spec)
    assert _run(tmp_path, monkeypatch, kinds=["extra"]) == 0
    assert seen == [1] and (tmp_path / f"{DAY}_extra.csv").exists()
    other = tmp_path / "zm"
    assert _run(other, monkeypatch, kinds=["extra"], tenant="ZM") == 0
    assert not other.exists()


class FailingAfter(FakeTransport):
    """Fails (non-retryable 400) from call number ``fail_from`` on, so earlier windows succeed."""

    def __init__(self, fail_from: int | None) -> None:
        super().__init__()
        self.fail_from = fail_from

    def post(self, url, headers, body, timeout):
        if self.fail_from is not None and self.calls + 1 >= self.fail_from:
            self.calls += 1
            return 400, b"boom"
        return super().post(url, headers, body, timeout)


def _parts_dir(tmp_path):
    return tmp_path.with_name(tmp_path.name + "_parts") / f"ZA_{DAY}"


def test_failure_at_part_n_keeps_earlier_parts_and_rerun_fetches_only_rest(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=FailingAfter(fail_from=6)) == 1
    assert sorted(p.name for p in _parts_dir(tmp_path).glob("ctap_*.json") if "manifest" not in p.name) == [f"ctap_{i:02d}.json" for i in range(1, 6)]
    resumed = FakeTransport()
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=resumed) == 0
    assert resumed.calls == 24 - 5 and (tmp_path / f"{DAY}_ctap.csv").exists()


def test_corrupted_part_is_refetched_on_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "cleanup_parts", lambda *args, **kwargs: False)
    _run(tmp_path, monkeypatch, kinds=["ctap"])
    (tmp_path / f"{DAY}_ctap.csv").unlink()
    (_parts_dir(tmp_path) / "ctap_03.json").write_text("[]", encoding="utf-8")
    again = FakeTransport()
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=again) == 0
    assert again.calls == 1


def test_fresh_ignores_all_parts(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, kinds=["ctap"])
    (tmp_path / f"{DAY}_ctap.csv").unlink()
    fresh = FakeTransport()
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    deps = runner.Dependencies(
        transport=fresh, tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=lambda d, drm: ("ok", True), report=runner.print_report,
        job_runner=SerialJobRunner(),
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get("ZA"), day=DAY, kinds=["ctap"], out_dir=tmp_path, force=False, fresh=True)
    assert runner.run_export(request, deps) == 0 and fresh.calls == 24


def test_part_hours_sets_window_count(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "cleanup_parts", lambda *args, **kwargs: False)
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    transport = FakeTransport()
    deps = runner.Dependencies(
        transport=transport, tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=lambda d, drm: ("ok", True), report=runner.print_report,
        job_runner=SerialJobRunner(),
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get("ZA"), day=DAY, kinds=["ctap"], out_dir=tmp_path, force=False, part_hours=6)
    assert runner.run_export(request, deps) == 0
    assert len(list(_parts_dir(tmp_path).glob("ctap_*.manifest.json"))) == 4


def test_part_log_lines_carry_no_token(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _run(tmp_path, monkeypatch, kinds=["ctap"])
    assert "parts total=24 reused=0 remaining=24" in caplog.text and TOKEN not in caplog.text


def test_part_hours_argument_is_validated():
    with pytest.raises(SystemExit):
        cli.parse_args(["--tenant", "ZA", "--part-hours", "0"])
    assert cli.parse_args(["--tenant", "ZA", "--fresh", "--part-hours", "6"]).part_hours == 6


def test_window_inside_ingestion_lag_is_not_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    today = datetime.now(timezone.utc).date().isoformat()
    deps = runner.Dependencies(
        transport=FakeTransport(), tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=lambda d, drm: ("ok", True), report=runner.print_report,
        job_runner=SerialJobRunner(),
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get("ZA"), day=today, kinds=["ctap"], out_dir=tmp_path, force=False, part_hours=24)
    assert runner.run_export(request, deps) == 0
    assert not (tmp_path.with_name(tmp_path.name + "_parts") / f"ZA_{today}").exists()


def test_export_request_rejects_invalid_part_hours(tmp_path):
    with pytest.raises(ValueError):
        runner.ExportRequest(tenant=TenantRegistry().get("ZA"), day=DAY, kinds=["ctap"], out_dir=tmp_path, force=False, part_hours=0)


def test_parts_folder_deleted_only_after_all_checks_pass(tmp_path, monkeypatch):
    sibling = _parts_dir(tmp_path).with_name("ZA_2026-10-28")
    sibling.mkdir(parents=True)
    assert _run(tmp_path, monkeypatch, kinds=["ctap"]) == 0
    assert not _parts_dir(tmp_path).exists() and sibling.exists()


def test_failed_input_check_keeps_parts_for_resume(tmp_path, monkeypatch):
    kinds = ["ctap", "smvod", "smvod-ts"]
    assert _run(tmp_path, monkeypatch, kinds=kinds, check=lambda directory, drm: ("FAIL", False)) == 1
    assert (_parts_dir(tmp_path) / "ctap_01.json").exists()


def test_failed_kind_keeps_parts(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=FailingAfter(fail_from=6)) == 1
    assert (_parts_dir(tmp_path) / "ctap_05.json").exists()


def test_tampered_output_row_count_keeps_parts(tmp_path, monkeypatch):
    original = runner._build_and_write

    def drop_rows(spec, request, series, path):
        return original(spec, request, [], path)

    monkeypatch.setattr(runner, "_build_and_write", drop_rows)
    assert _run(tmp_path, monkeypatch, kinds=["ctap"]) == 1
    assert (_parts_dir(tmp_path) / "ctap_01.json").exists() and not (tmp_path / f"{DAY}_ctap.csv").exists()


def test_other_kinds_resume_parts_block_cleanup(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, kinds=["smvod"], transport=FailingAfter(fail_from=6)) == 1
    assert _run(tmp_path, monkeypatch, kinds=["ctap"]) == 0
    assert (_parts_dir(tmp_path) / "smvod_01.json").exists()


def test_uncached_window_is_a_gap_and_keeps_run_ok(tmp_path, monkeypatch, caplog):
    today = datetime.now(timezone.utc).date().isoformat()
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    deps = runner.Dependencies(
        transport=FakeTransport(), tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=lambda d, drm: ("ok", True), report=runner.print_report,
        job_runner=SerialJobRunner(),
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get("ZA"), day=today, kinds=["ctap"], out_dir=tmp_path, force=False, part_hours=24)
    assert runner.run_export(request, deps) == 0
    assert "missing or failed verification" in caplog.text


def test_resume_skipping_verified_existing_output_still_cleans_up(tmp_path, monkeypatch):
    real_cleanup = runner.cleanup_parts
    monkeypatch.setattr(runner, "cleanup_parts", lambda *args, **kwargs: False)
    assert _run(tmp_path, monkeypatch, kinds=["ctap"]) == 0
    monkeypatch.setattr(runner, "cleanup_parts", real_cleanup)
    assert _parts_dir(tmp_path).exists()
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=FakeTransport()) == 0
    assert not _parts_dir(tmp_path).exists()


def test_parallel_run_writes_same_files_as_serial(tmp_path, monkeypatch):
    serial, parallel = tmp_path / "serial", tmp_path / "parallel"
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], out=serial, workers=1) == 0
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], out=parallel, workers=4) == 0
    name = f"{DAY}_ctap.csv"
    assert (serial / name).read_bytes() == (parallel / name).read_bytes()


def test_worker_logs_carry_fcid_and_no_token(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    api_logger = logging.getLogger("scripts.lib.lightstep_api")
    api_logger.addFilter(FcidLogFilter())
    bind_fcid("worker-fcid-test")
    seen_fcids: list[str | None] = []

    class LoggingTransport(FakeTransport):
        def post(self, url, headers, body, timeout):
            from src.lib.logging.context import current_fcid
            seen_fcids.append(current_fcid())
            return super().post(url, headers, body, timeout)

    try:
        assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=LoggingTransport(), workers=4) == 0
    finally:
        api_logger.filters.clear()
    assert seen_fcids and set(seen_fcids) == {"worker-fcid-test"}
    assert TOKEN not in caplog.text


def test_parallel_failure_stops_new_windows_keeps_parts_and_rerun_resumes(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=FailingAfter(fail_from=6), workers=3) == 1
    kept = [p for p in _parts_dir(tmp_path).glob("ctap_*.json") if "manifest" not in p.name]
    assert 5 <= len(kept) < 24
    resumed = FakeTransport()
    assert _run(tmp_path, monkeypatch, kinds=["ctap"], transport=resumed, workers=3) == 0
    assert resumed.calls == 24 - len(kept)


def test_workers_outside_bounds_rejected():
    for bad in ("0", "9"):
        with pytest.raises(SystemExit):
            cli.parse_args(["--tenant", "ZA", "--workers", bad])
    assert cli.parse_args(["--tenant", "ZA", "--workers", "8"]).workers == 8
    with pytest.raises(ValueError):
        ThreadJobRunner(0)


def test_runner_works_with_injected_serial_runner(tmp_path, monkeypatch):
    import threading
    before = threading.active_count()
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    deps = runner.Dependencies(
        transport=FakeTransport(), tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=lambda directory, drm: ("ok", True), report=runner.print_report, job_runner=SerialJobRunner(),
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get("ZA"), day=DAY, kinds=["ctap"], out_dir=tmp_path, force=False)
    assert runner.run_export(request, deps) == 0 and threading.active_count() == before


class EmptyForTransport(FakeTransport):
    """Returns zero series for queries containing ``marker``."""

    def __init__(self, marker: str) -> None:
        super().__init__()
        self.marker = marker

    def post(self, url, headers, body, timeout):
        if self.marker in json.loads(body)["data"]["attributes"]["query"]:
            return 200, json.dumps({"data": {"attributes": {"series": []}}}).encode()
        return super().post(url, headers, body, timeout)


def test_empty_kind_within_retention_writes_header_only_csv_and_warns(tmp_path, monkeypatch, caplog, capsys):
    monkeypatch.setattr(runner, "utc_now", lambda: datetime(2026, 10, 31, tzinfo=timezone.utc))
    with caplog.at_level(logging.WARNING):
        assert _run(tmp_path, monkeypatch, transport=EmptyForTransport("go-mdrmfe")) == 0
    lines = (tmp_path / f"{DAY}_mdrmfe.csv").read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 1 and len((tmp_path / f"{DAY}_ctap.csv").read_text(encoding="utf-8-sig").splitlines()) > 1
    assert any("tenant=ZA kind=mdrmfe day=2026-10-29" in r.getMessage() and r.levelno == logging.WARNING for r in caplog.records)
    assert "WARNING  mdrmfe: no series returned" in capsys.readouterr().out


def test_empty_kind_older_than_retention_is_a_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "utc_now", lambda: datetime(2026, 11, 20, tzinfo=timezone.utc))
    assert _run(tmp_path, monkeypatch, kinds=["mdrmfe"], transport=EmptyForTransport("go-mdrmfe")) == 1
    assert not (tmp_path / f"{DAY}_mdrmfe.csv").exists()


def test_retention_window_is_judged_by_the_day_not_by_emptiness():
    now = datetime(2026, 11, 4, 8, tzinfo=timezone.utc)
    assert not runner.outside_retention("2026-11-02", now) and not runner.outside_retention("2026-10-29", now)
    assert runner.outside_retention("2026-10-28", now)
