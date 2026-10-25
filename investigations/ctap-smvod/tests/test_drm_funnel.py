from __future__ import annotations

import pytest
from lib.drm_exports import LrmRow, MdrmfeRow

from lib import drm_funnel as mod


def _fe(session: str, fcid: str, drm: str = "widevine", status: str = "201") -> MdrmfeRow:
    return MdrmfeRow(session, fcid, "H", "D", "LOW", drm, status)


def _lrm(fcid: str, status: str = "200") -> LrmRow:
    return LrmRow(fcid, "D", status)


def _by_key(result: mod.FunnelResult, field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in result.rows:
        out[getattr(r, field)] = out.get(getattr(r, field), 0) + r.sessions
    return out


def test_every_session_in_exactly_one_bucket_and_outcome() -> None:
    sessions = [
        mod.SessionInput("abr-vod-1"), mod.SessionInput("abr-vod-2", "3016; 3016"),
        mod.SessionInput("abr-linear-3"), mod.SessionInput("abr-vod-4", "6001"),
        mod.SessionInput("abr-vod-1"),  # duplicate row in the merge
    ]
    fe = [_fe("abr-vod-1", "F1"), _fe("abr-vod-2", "F2", "fairplay", "403"), _fe("abr-linear-3", "F3")]
    lrm = [_lrm("F1"), _lrm("F3", "400")]
    result = mod.build_funnel("ZA", "2026-10-23", sessions, fe, lrm)

    assert sum(r.sessions for r in result.rows) == 4 == result.totals["sessions"]
    assert _by_key(result, "drm_bucket") == {"widevine": 2, "fairplay": 1, "no_drm_activity": 1}
    assert _by_key(result, "license_outcome") == {"success": 1, "failed": 2, "no_request": 1}
    assert _by_key(result, "error_group") == {"no_error": 2, "3016": 1, "6xxx": 1}
    assert _by_key(result, "kind") == {"vod": 3, "linear": 1}
    assert result.totals["drm_requested"] == 3
    assert result.totals["license_success"] == 1
    assert result.totals["errored"] == 2


def test_drm_only_sessions_are_counted_and_tagged() -> None:
    result = mod.build_funnel(
        "GH", "2026-10-23", [mod.SessionInput("abr-vod-1")],
        [_fe("abr-vod-1", "F1"), _fe("abr-vod-9", "F9"), _fe("weird-5", "F5")], [_lrm("F1"), _lrm("F9")],
    )
    assert _by_key(result, "source") == {"merge": 1, "drm_only": 2}
    assert result.totals["drm_only"] == 2
    assert _by_key(result, "kind") == {"vod": 2, "other": 1}


def test_retry_then_success_and_mixed_drm_type() -> None:
    fe = [
        _fe("abr-vod-1", "F1", status="403"), _fe("abr-vod-1", "F2"),
        _fe("abr-vod-2", "G1", "widevine"), _fe("abr-vod-2", "G2", "fairplay"),
    ]
    lrm = [_lrm("F1", "400"), _lrm("F2"), _lrm("G1"), _lrm("G2")]
    sessions = [mod.SessionInput("abr-vod-1"), mod.SessionInput("abr-vod-2")]
    result = mod.build_funnel("ZM", "2026-10-23", sessions, fe, lrm)
    assert _by_key(result, "license_outcome") == {"retry_then_success": 1, "success": 1}
    assert _by_key(result, "drm_bucket") == {"widevine": 1, "mixed": 1}
    assert result.totals["license_success"] == 2


def test_success_then_failure_is_failed_and_blank_type_is_ignored() -> None:
    fe = [_fe("abr-vod-1", "F1"), _fe("abr-vod-1", "F2", status="403"),
          _fe("abr-vod-2", "G1", ""), _fe("abr-vod-2", "G2", "widevine")]
    lrm = [_lrm("F1"), _lrm("F2", "400"), _lrm("G1"), _lrm("G2")]
    result = mod.build_funnel("ZA", "d", [mod.SessionInput("abr-vod-1"), mod.SessionInput("abr-vod-2")], fe, lrm)
    assert _by_key(result, "license_outcome") == {"failed": 1, "success": 1}
    assert _by_key(result, "drm_bucket") == {"widevine": 2}


def test_empty_session_id_is_ignored() -> None:
    result = mod.build_funnel(
        "ZA", "2026-10-23", [mod.SessionInput(""), mod.SessionInput("abr-vod-1")],
        [_fe("", "F0")], [], flat_errors=[("", "3016")],
    )
    assert result.totals["sessions"] == 1
    assert result.totals["drm_only"] == 0 and result.totals["errored"] == 0


def test_201_without_lrm_row_is_failed_and_flat_error_fills_gap() -> None:
    result = mod.build_funnel(
        "ZA", "2026-10-23", [mod.SessionInput("abr-vod-1")], [_fe("abr-vod-1", "F1")], [],
        flat_errors=[("abr-vod-1", "3016"), ("abr-vod-1", "6001")],
    )
    assert _by_key(result, "license_outcome") == {"failed": 1}
    assert _by_key(result, "error_group") == {"3016": 1}


@pytest.mark.parametrize(
    "code,group",
    [("", "no_error"), ("3015", "3015"), ("1003", "1xxx"), ("6007", "6xxx"), ("E31012", "E31012"), ("3017", "3017")],
)
def test_error_group(code: str, group: str) -> None:
    assert mod.error_group(code) == group


def test_error_code_counts_sum_to_errored_sessions() -> None:
    sessions = [
        mod.SessionInput("abr-vod-1", "6001; 3016"), mod.SessionInput("abr-vod-2", "E31012"),
        mod.SessionInput("abr-vod-3", "3016"), mod.SessionInput("abr-vod-4"),
    ]
    result = mod.build_funnel("ZA", "2026-10-23", sessions, [], [])
    codes = _by_key(result, "error_code")
    assert codes == {"6001": 1, "E31012": 1, "3016": 1, "no_error": 1}
    assert sum(n for c, n in codes.items() if c != "no_error") == result.totals["errored"] == 3
