from __future__ import annotations

from build_3016_drm_device_summary import summarise


def _ev(hh: str, status: str = "200", model: str = "a05s", sub: str = "Video decode error") -> dict:
    return {"opco": "ZA", "subcategory": sub, "cdm_make": "Samsung" if model else "", "cdm_model": model,
            "security_level": "L1" if model else "", "household_id": hh, "license_status": status}


def test_device_summary_counts_distinct_households() -> None:
    rows = summarise([_ev("h1"), _ev("h1", "500"), _ev("h2")])
    assert rows == [{"opco": "ZA", "subcategory": "Video decode error", "cdm_make": "Samsung",
                     "cdm_model": "a05s", "security_level": "L1", "events": 3, "households": 2, "license_ok": 2}]


def test_unjoined_events_group_under_empty_model_and_skip_empty_households() -> None:
    rows = summarise([_ev("", "", model=""), _ev("", "", model="")])
    assert len(rows) == 1
    assert (rows[0]["cdm_model"], rows[0]["events"], rows[0]["households"], rows[0]["license_ok"]) == ("", 2, 0, 0)
