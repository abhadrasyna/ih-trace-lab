"""Offline tests for har_identity_timeline (synthetic entries only)."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "har_identity_timeline.py"
spec = importlib.util.spec_from_file_location("har_identity_timeline", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _jwt(claims: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"h.{body}.s"


def _entry(url: str, **req) -> dict:
    return {"startedDateTime": "t", "request": {"url": url, "method": "GET", **req}, "response": {"status": 200}}


def test_query_and_jwt_claims_extracted_without_token_value():
    entry = _entry(
        "https://h/p?hhid=H1&x=1",
        queryString=[{"name": "hhid", "value": "H1"}],
        headers=[{"name": "Authorization", "value": "Bearer " + _jwt({"sub": "u1", "exp": 1})}],
    )
    rows = mod.entry_rows(0, entry)
    assert {(r["key"], r["value"]) for r in rows} == {("hhid", "H1"), ("sub", "u1")}


def test_media_and_malformed_jwt_are_ignored():
    assert mod.entry_rows(0, _entry("https://h/seg1.m4s?hhid=H1")) == []
    assert mod.decode_jwt_claims("not-a-jwt") == {}


def test_snake_case_form_body_and_non_http_url():
    entry = _entry(
        "wss://h/sock?access_token=SECRET#frag",
        postData={"text": "grant_type=authorization_code&client_id=C1&code=SECRET"},
    )
    rows = mod.entry_rows(0, entry)
    assert {(r["key"], r["value"]) for r in rows} == {("grant_type", "authorization_code"), ("client_id", "C1")}
    assert all("SECRET" not in str(r) for r in rows)
