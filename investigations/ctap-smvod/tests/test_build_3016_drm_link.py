from __future__ import annotations

from build_3016_drm_link import JOINED, NO_CDM_ROW, NO_LICENSE_REQUEST, link
from lib.drm_exports import CdmRow, LrmRow, MdrmfeRow

SID = "abr-vod-21f5d080-e427-453f-aa09-edbbabd92a4e"
FCID = "6ADCA78ABAA1B5290003C530"


def _fe(sid: str = SID, fcid: str = FCID, status: str = "201", drm: str = "widevine") -> MdrmfeRow:
    return MdrmfeRow(sid, fcid, "H1", "D1", "LOW", drm, status)


def test_session_joins_to_cdm_via_fcid() -> None:
    cdm = [CdmRow(FCID, "widevine", "Samsung", "a05s", "ANDROID", "L1")]
    (row,) = link([{"sessionId": SID}], [_fe()], cdm, [LrmRow(FCID, "D1", "200")])
    assert row["drm_join"] == JOINED
    assert (row["cdm_make"], row["cdm_model"], row["security_level"], row["br_ref"]) == ("Samsung", "a05s", "L1", "LOW")
    assert (row["household_id"], row["device_id"], row["fcid"], row["license_status"]) == ("H1", "D1", FCID, "200")


def test_missing_rows_give_explicit_outcomes() -> None:
    events = [{"sessionId": SID}, {"sessionId": "other"}]
    out = link(events, [_fe()], [CdmRow(FCID, "playready", "x", "y", "", "")], [])
    assert [r["drm_join"] for r in out] == [NO_CDM_ROW, NO_LICENSE_REQUEST]
    assert out[1]["fcid"] == "" and len(out) == len(events)


def test_empty_keys_never_join() -> None:
    cdm = [CdmRow("", "widevine", "x", "y", "", "")]
    out = link([{"sessionId": ""}, {"sessionId": SID}], [_fe(sid=""), _fe(fcid="")], cdm, [LrmRow("", "", "200")])
    assert out[0]["drm_join"] == NO_LICENSE_REQUEST
    assert out[1]["drm_join"] == NO_CDM_ROW


def test_retries_keep_latest_successful_else_latest() -> None:
    rows = [_fe(fcid="A", status="201"), _fe(fcid="B", status="500")]
    assert link([{"sessionId": SID}], rows, [], [])[0]["fcid"] == "A"
    rows = [_fe(fcid="A", status="500"), _fe(fcid="B", status="403")]
    assert link([{"sessionId": SID}], rows, [], [])[0]["fcid"] == "B"


def test_conflicting_cdm_rows_raise_but_identical_collapse() -> None:
    import pytest

    a = CdmRow(FCID, "widevine", "Samsung", "a05s", "ANDROID", "L1")
    assert link([{"sessionId": SID}], [_fe()], [a, a], [])[0]["drm_join"] == JOINED
    with pytest.raises(ValueError, match="conflicting"):
        link([{"sessionId": SID}], [_fe()], [a, CdmRow(FCID, "widevine", "X", "y", "", "")], [])


def test_existing_drm_column_in_events_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="platform"):
        link([{"sessionId": SID, "platform": "x"}], [], [], [])
