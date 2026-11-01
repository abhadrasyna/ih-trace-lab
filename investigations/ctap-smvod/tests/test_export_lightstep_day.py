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


def _run(tmp_path, monkeypatch, *, kinds=ALL_KINDS, transport=None, check=None, force=False, tenant="ZA"):
    monkeypatch.setenv("LIGHTSTEP_API_KEY_EU", TOKEN)
    monkeypatch.setenv("LIGHTSTEP_API_KEY_US", TOKEN)
    deps = runner.Dependencies(
        transport=transport or FakeTransport(), tokens=runner.EnvTokenProvider(), resolve_target=kinds_mod.resolve_target,
        input_check=check or (lambda directory, drm: ("ok", True)), report=runner.print_report,
    )
    request = runner.ExportRequest(tenant=TenantRegistry().get(tenant), day=DAY, kinds=kinds, out_dir=tmp_path, force=force)
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


def test_output_dir_argument_redirects_csvs_and_check(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "init_logging", lambda slug: "fcid")
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
