"""Two-step token flow: client-credentials access token, then a silent-login token for a household."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

AUTH_URL = "https://auth.synamedia.com/oauth/token"
CREATE_TOKEN_URL = "https://manage.client-identity.synamedia.com/silent-login/create-token"
AUDIENCE = "https://projects.synamedia.com"
CLIENT_ID_VAR = "SYNAMEDIA_CLIENT_ID"
CLIENT_SECRET_VAR = "SYNAMEDIA_CLIENT_SECRET"

# (url, headers, json body) -> parsed JSON response; injectable so tests never touch the network.
PostJson = Callable[[str, Mapping[str, str], Mapping[str, Any]], dict[str, Any]]


class TokenError(RuntimeError):
    """Raised on a failed HTTP call, malformed response, or missing credentials."""


def post_json(url: str, headers: Mapping[str, str], body: Mapping[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=dict(headers), method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed https URLs
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise TokenError(f"POST {url} failed: HTTP {exc.code} {exc.read().decode(errors='replace')}") from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise TokenError(f"POST {url} failed: {exc}") from exc


def credentials_from_env(env: Mapping[str, str] | None = None) -> tuple[str, str]:
    source = os.environ if env is None else env
    missing = [name for name in (CLIENT_ID_VAR, CLIENT_SECRET_VAR) if not source.get(name)]
    if missing:
        raise TokenError(f"Missing environment variable(s): {', '.join(missing)}")
    return source[CLIENT_ID_VAR], source[CLIENT_SECRET_VAR]


def get_access_token(client_id: str, client_secret: str, post: PostJson = post_json) -> str:
    response = post(
        AUTH_URL,
        {"Accept": "application/json", "Content-Type": "application/json"},
        {
            "grant_type": "client_credentials",
            "audience": AUDIENCE,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    token = response.get("access_token")
    if not token:
        raise TokenError("Auth response has no access_token")
    return str(token)


def create_silent_login_token(
    access_token: str, household_id: str, expires_in: int = 3600, post: PostJson = post_json
) -> dict[str, Any]:
    return post(
        CREATE_TOKEN_URL,
        {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
        {"subject": household_id, "expires_in": expires_in},
    )
