"""Offline tests for the token flow; HTTP is replaced by a recording fake."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.lib.token_gen import client
from src.lib.token_gen.cli import load_env_file, main


def test_get_access_token_posts_client_credentials() -> None:
    calls = []

    def fake(url, headers, body):
        calls.append((url, dict(body)))
        return {"access_token": "tok"}

    assert client.get_access_token("id", "secret", post=fake) == "tok"
    assert calls[0][0] == client.AUTH_URL
    assert calls[0][1]["grant_type"] == "client_credentials"


def test_get_access_token_missing_token_raises() -> None:
    with pytest.raises(client.TokenError):
        client.get_access_token("id", "secret", post=lambda *_: {"error": "denied"})


def test_create_silent_login_token_sends_bearer_and_subject() -> None:
    seen = {}

    def fake(url, headers, body):
        seen.update(url=url, headers=dict(headers), body=dict(body))
        return {"token": "silent"}

    result = client.create_silent_login_token("abc", "hh-1", 600, post=fake)
    assert result == {"token": "silent"}
    assert seen["headers"]["Authorization"] == "Bearer abc"
    assert seen["body"] == {"subject": "hh-1", "expires_in": 600}


def test_credentials_from_env_missing_raises() -> None:
    with pytest.raises(client.TokenError, match="SYNAMEDIA_CLIENT_SECRET"):
        client.credentials_from_env({"SYNAMEDIA_CLIENT_ID": "x"})


def test_load_env_file_parses_and_tolerates_missing(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("# c\nSYNAMEDIA_CLIENT_ID='a'\nexport SYNAMEDIA_CLIENT_SECRET=b\n")
    assert load_env_file(env) == {"SYNAMEDIA_CLIENT_ID": "a", "SYNAMEDIA_CLIENT_SECRET": "b"}
    assert load_env_file(tmp_path / "nope") == {}


def test_main_reports_missing_credentials(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("SYNAMEDIA_CLIENT_ID", raising=False)
    monkeypatch.delenv("SYNAMEDIA_CLIENT_SECRET", raising=False)
    assert main(["hh-1", "--env-file", str(tmp_path / "none")]) == 1
    assert "Missing environment" in capsys.readouterr().err
