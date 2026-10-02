"""`AuthProtocol` conformance tests for the concrete `SsoAuth` implementer."""
from __future__ import annotations

from src.lib.auth.protocols import AuthProtocol
from src.lib.auth.sso import SsoAuth


class _StubRefresher:
    def ensure_valid(self) -> bool:
        return True


class _StubSession:
    """Stand-in for `boto3.Session` -- never a real boto3 object, so no AWS dependency in tests."""


def test_sso_auth_satisfies_auth_protocol() -> None:
    auth = SsoAuth(
        refresher_factory=lambda profile_name: _StubRefresher(),
        session_factory=lambda profile_name: _StubSession(),
    )
    assert isinstance(auth, AuthProtocol)

