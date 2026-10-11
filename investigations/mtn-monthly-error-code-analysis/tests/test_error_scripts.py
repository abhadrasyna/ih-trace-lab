from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parents[2]))

import profile_error_code  # noqa: E402
import summarize_error_devices  # noqa: E402
from mec_lib import error_events, ua_device  # noqa: E402

ANDROID_WV = "Mozilla/5.0 (Linux; Android 15; SM-A055F Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"


def row(mid: str, session: str, household: str, ua: str = ANDROID_WV, **extra: str) -> dict[str, str]:
    base = {"messageid": mid, "sessionId": session, "householdId": household, "deviceId": f"d-{household}",
            "errorcode": "3016", "user_agent": ua, "is_wv": "true", "position": "0"}
    return {**base, **extra}


def test_parse_device_extracts_model_android_build() -> None:
    assert ua_device.parse_device(ANDROID_WV) == ("SM-A055F", "15", "AP3A.240905.015.A2")


def test_parse_device_blank_for_non_android_and_families() -> None:
    assert ua_device.parse_device(IPHONE) == ("", "", "")
    assert ua_device.ua_family(IPHONE) == "iOS"
    assert ua_device.ua_family("") == "(blank)"


def test_dedupe_keeps_first_messageid_and_rejects_blank() -> None:
    rows = [row("m1", "s1", "h1"), row("m1", "s1", "h1"), row("m2", "s2", "h1")]
    assert len(error_events.dedupe_events(rows)) == 2
    with pytest.raises(ValueError):
        error_events.dedupe_events([row("", "s1", "h1")])


def test_read_events_fails_on_missing_identity_column(tmp_path: Path) -> None:
    bad = tmp_path / "2026-10-08_3016.csv"
    bad.write_text("messageid,errorcode\nm1,3016\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sessionId"):
        error_events.read_events(bad)


def test_find_files_raises_when_code_has_no_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        error_events.find_files(tmp_path, "3016")


def test_position_bucket_values() -> None:
    assert [profile_error_code.position_bucket(v) for v in ("0", "0.0", "12.5", "", "x")] == ["0", "0", ">0", "(blank)", "(non-numeric)"]


def test_position_bucket_flags_non_finite_and_negative() -> None:
    assert [profile_error_code.position_bucket(v) for v in ("NaN", "-1", "inf")] == ["(invalid)"] * 3


def test_sessions_per_group_skips_blank_sessions() -> None:
    rows = [{"sessionId": "s1", "householdId": "h1"}, {"sessionId": "", "householdId": "h1"}]
    assert error_events.sessions_per_group(rows, "householdId") == {"h1": 1}


def test_select_files_rejects_unknown_date() -> None:
    files = [("2026-10-08", Path("a.csv"))]
    assert error_events.select_files(files, None) == files
    with pytest.raises(FileNotFoundError, match="2026-10-07"):
        error_events.select_files(files, ["2026-10-07"])


def test_profile_counts_sessions_households_and_absent_column() -> None:
    rows = [row("m1", "s1", "h1"), row("m2", "s2", "h1"), row("m3", "s3", "h2")]
    profile = profile_error_code.build_profile(list(rows[0]), rows)
    assert (profile["events"], profile["sessions"], profile["households"]) == (3, 3, 2)
    assert profile["sessions_per_household"] == 1.5
    assert profile["columns"]["pipeline_status"] is None
    assert profile["columns"]["position_bucket"]["0"] == 3


def test_profile_zero_households_does_not_divide_by_zero() -> None:
    assert profile_error_code.concentration([{"sessionId": "s1", "householdId": ""}]) == {"sessions_per_household": 0.0}


def test_device_summary_dedups_and_keeps_unparsed_family() -> None:
    rows = [row("m1", "s1", "h1"), row("m2", "s2", "h1"), row("m3", "s3", "h2", ua=IPHONE, is_wv="false")]
    summary = summarize_error_devices.summarize_devices(rows)
    top = summary[0]
    assert (top["device_model"], top["events"], top["sessions"], top["households"]) == ("SM-A055F", 2, 2, 1)
    unparsed = [r for r in summary if r["device_model"] == "(unparsed)"][0]
    assert unparsed["android_or_family"] == "iOS"


def test_device_summary_with_build_splits_groups() -> None:
    other = "Mozilla/5.0 (Linux; Android 15; SM-A055F Build/OTHER.1; wv)"
    rows = [row("m1", "s1", "h1"), row("m2", "s2", "h2", ua=other)]
    assert len(summarize_error_devices.summarize_devices(rows)) == 1
    assert len(summarize_error_devices.summarize_devices(rows, with_build=True)) == 2
