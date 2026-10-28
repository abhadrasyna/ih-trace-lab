"""Tests for lib/lightstep_inputs.py (Step 0 validation of the manual Lightstep CSVs)."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import load_script

load_script("check_lightstep_inputs.py")  # puts scripts/ on sys.path so `lib` imports resolve
from lib import lightstep_inputs as li  # noqa: E402
from lib.tenant_context import TenantContext  # noqa: E402

DATE = "2026-10-26"
SETTINGS = li.Settings()


def _context(shared: bool = False) -> TenantContext:
    return TenantContext(
        code="ZM", athena_tenant_id="a", database="d", debug_events_table="t", profile="p", region="r",
        lightstep_project="proj", disambiguation_attribute="sessionInfo.busUnitId" if shared else None,
        disambiguation_value="dtunf6yo" if shared else None,
    )


def _us(hour: int, minute: int = 0) -> str:
    moment = datetime(2026, 10, 26, hour, minute, tzinfo=timezone.utc)
    return str(int(moment.timestamp() * 1_000_000))


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _ctap(path: Path) -> None:
    _write(path, ["http.user_agent", "lightstep.trace_id"], [["ua", "1"]])


def _smvod(path: Path) -> None:
    _write(path, ["householdId", "deviceId", "sessionId", "lightstep.trace_id"], [["h", "d", "s", "1"]])


def _smvod_ts(path: Path, first: tuple[int, int] = (0, 5), last: tuple[int, int] = (23, 55), rows: int = 2) -> None:
    body = [["s", _us(*first), _us(*last)]] + [["s", _us(*first), _us(*first)]] * (rows - 1)
    _write(path, ["sessionId", "oldest_micros", "youngest_micros"], body)


def _day(folder: Path) -> None:
    _ctap(folder / f"{DATE}_ctap.csv")
    _smvod(folder / f"{DATE}_smvod.csv")
    _smvod_ts(folder / f"{DATE}_smvod-ts.csv")


def _levels(findings: list[li.Finding], level: str = li.FAIL) -> list[tuple[str, str]]:
    return [(f.check, f.subject) for f in findings if f.level == level]


def test_complete_whole_day_set_has_no_failures(tmp_path: Path) -> None:
    _day(tmp_path)

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert not li.has_failures(findings)
    assert ("coverage", "smvod-ts") in _levels(findings, li.PASS)


def test_missing_smvod_ts_fails_presence(tmp_path: Path) -> None:
    _day(tmp_path)
    (tmp_path / f"{DATE}_smvod-ts.csv").unlink()

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("presence", "smvod-ts") in _levels(findings)


def test_parts_only_set_passes_with_contiguous_numbering(tmp_path: Path) -> None:
    for number, (first, last) in enumerate([((0, 5), (11, 55)), ((12, 0), (23, 55))], start=1):
        _ctap(tmp_path / f"{DATE}_{number:02d}_ctap.csv")
        _smvod(tmp_path / f"{DATE}_{number:02d}_smvod.csv")
        _smvod_ts(tmp_path / f"{DATE}_{number:02d}_smvod-ts.csv", first, last)

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert not li.has_failures(findings)


def test_numbering_gap_fails_for_core_but_only_warns_for_drm(tmp_path: Path) -> None:
    _day(tmp_path)
    _ctap(tmp_path / f"{DATE}_01_ctap.csv")
    _ctap(tmp_path / f"{DATE}_03_ctap.csv")
    for number in (1, 3):
        _write(tmp_path / f"{DATE}_{number:02d}_mdrm-cdm-playready.csv", list(li.ARTIFACT_COLUMNS["mdrm-cdm-playready"]), [["f", "m", "x"]])

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("parts", "ctap") in _levels(findings)
    assert ("parts", "mdrm-cdm-playready") in _levels(findings, li.WARN)
    assert ("parts", "mdrm-cdm-playready") not in _levels(findings)


def test_core_artifacts_must_have_the_same_parts(tmp_path: Path) -> None:
    for kind_writer, kind in ((_ctap, "ctap"), (_smvod, "smvod")):
        kind_writer(tmp_path / f"{DATE}_01_{kind}.csv")
    _ctap(tmp_path / f"{DATE}_02_ctap.csv")
    _smvod_ts(tmp_path / f"{DATE}_01_smvod-ts.csv", (0, 5), (23, 55))
    _smvod_ts(tmp_path / f"{DATE}_02_smvod-ts.csv", (0, 5), (23, 55))

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("part-set", "smvod") in _levels(findings)
    assert ("part-set", "ctap") not in _levels(findings)


def test_combined_file_built_from_a_deleted_part_fails(tmp_path: Path) -> None:
    _day(tmp_path)
    _ctap(tmp_path / f"{DATE}_01_ctap.csv")
    sidecar = tmp_path / f"{DATE}_ctap.csv{li.SIDECAR_SUFFIX}"
    sidecar.write_text(json.dumps({"parts": [f"{DATE}_01_ctap.csv", f"{DATE}_02_ctap.csv"]}), encoding="utf-8")

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("combined-from", "ctap") in _levels(findings)


def test_missing_column_and_empty_file_fail(tmp_path: Path) -> None:
    _day(tmp_path)
    _write(tmp_path / f"{DATE}_ctap.csv", ["http.user_agent"], [["ua"]])
    _write(tmp_path / f"{DATE}_smvod.csv", ["householdId", "deviceId", "sessionId", "lightstep.trace_id"], [])

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("schema", "ctap") in _levels(findings)
    assert ("rows", "smvod") in _levels(findings)


def test_foreign_tenant_rows_fail_for_shared_project(tmp_path: Path) -> None:
    _day(tmp_path)
    _write(tmp_path / f"{DATE}_ctap.csv", ["http.user_agent", "lightstep.trace_id", "sessionInfo.busUnitId"], [["ua", "1", "other"]])

    findings = li.validate_tenant(tmp_path, DATE, _context(shared=True), SETTINGS)

    assert ("tenant", "ctap") in _levels(findings)


@pytest.mark.parametrize(("first", "last"), [((5, 47), (23, 55)), ((0, 5), (22, 52))])
def test_day_edges_outside_tolerance_fail(tmp_path: Path, first: tuple[int, int], last: tuple[int, int]) -> None:
    _day(tmp_path)
    _smvod_ts(tmp_path / f"{DATE}_smvod-ts.csv", first, last)

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("coverage", "smvod-ts") in _levels(findings)


def test_gap_between_parts_fails(tmp_path: Path) -> None:
    for kind_writer, kind in ((_ctap, "ctap"), (_smvod, "smvod")):
        for number in (1, 2):
            kind_writer(tmp_path / f"{DATE}_{number:02d}_{kind}.csv")
    _smvod_ts(tmp_path / f"{DATE}_01_smvod-ts.csv", (0, 5), (8, 0))
    _smvod_ts(tmp_path / f"{DATE}_02_smvod-ts.csv", (10, 0), (23, 55))

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("gap", "smvod-ts") in _levels(findings)


def test_last_part_at_row_cap_warns_when_day_edge_is_reached(tmp_path: Path) -> None:
    _day(tmp_path)
    _smvod_ts(tmp_path / f"{DATE}_smvod-ts.csv", rows=SETTINGS.row_cap)

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("row-cap", "smvod-ts") in _levels(findings, li.WARN)
    assert not li.has_failures(findings)


def test_non_numeric_timestamp_fails_loudly(tmp_path: Path) -> None:
    _day(tmp_path)
    _write(tmp_path / f"{DATE}_smvod-ts.csv", ["sessionId", "oldest_micros", "youngest_micros"], [["s", "abc", "1"]])

    findings = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)

    assert ("coverage", "smvod-ts") in _levels(findings)


def test_drm_exports_required_only_with_include_drm(tmp_path: Path) -> None:
    _day(tmp_path)

    without = li.validate_tenant(tmp_path, DATE, _context(), SETTINGS)
    with_drm = li.validate_tenant(tmp_path, DATE, _context(), li.Settings(include_drm=True))

    assert ("presence", "mdrmfe") not in _levels(without)
    assert ("presence", "mdrmfe") in _levels(with_drm) and ("presence", "mdrm-lrm") in _levels(with_drm)
