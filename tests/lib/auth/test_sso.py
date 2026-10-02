"""Tests for `src.lib.auth.sso.SsoAuth`."""
from __future__ import annotations

from typing import Any

from src.lib.auth.sso import SsoAuth


class _FakeRefresher:
    def __init__(self, *, already_valid: bool) -> None:
        self.already_valid = already_valid
        self.ensure_valid_calls = 0

    def ensure_valid(self) -> bool:
        self.ensure_valid_calls += 1
        return self.already_valid


class _FakeSession:
    """Stand-in for `boto3.Session` -- never a real boto3 object, so no AWS dependency in tests."""


def test_ensure_session_delegates_to_upstream() -> None:
    refresher = _FakeRefresher(already_valid=True)
    refresher_calls: list[str] = []

    def refresher_factory(profile_name: str) -> _FakeRefresher:
        refresher_calls.append(profile_name)
        return refresher

    session_calls: list[str] = []

    def session_factory(profile_name: str) -> Any:
        session_calls.append(profile_name)
        return _FakeSession()

    auth = SsoAuth(refresher_factory=refresher_factory, session_factory=session_factory)

    result = auth.ensure_session("my-profile")

    assert isinstance(result, _FakeSession)
    assert refresher_calls == ["my-profile"]
    assert session_calls == ["my-profile"]
    assert refresher.ensure_valid_calls == 1


def test_refresh_if_expired_reports_whether_a_refresh_happened() -> None:
    already_valid_refresher = _FakeRefresher(already_valid=True)
    stale_refresher = _FakeRefresher(already_valid=False)

    auth_already_valid = SsoAuth(
        refresher_factory=lambda profile_name: already_valid_refresher,
        session_factory=lambda profile_name: _FakeSession(),
    )
    auth_stale = SsoAuth(
        refresher_factory=lambda profile_name: stale_refresher,
        session_factory=lambda profile_name: _FakeSession(),
    )

    assert auth_already_valid.refresh_if_expired("profile-a") is False
    assert auth_stale.refresh_if_expired("profile-b") is True


def test_ensure_session_does_not_construct_own_boto3_client() -> None:
    import ast
    import inspect

    source = inspect.getsource(SsoAuth)
    tree = ast.parse(source)

    boto3_references = [
        node
        for node in ast.walk(tree)
        if (
            (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "boto3")
            or (isinstance(node, ast.Name) and node.id == "boto3")
            or (isinstance(node, ast.ImportFrom) and node.module == "boto3")
        )
    ]

    assert not boto3_references, "SsoAuth must delegate all boto3 access to injected collaborators"


def test_refresh_failure_propagates_instead_of_being_swallowed() -> None:
    """`ensure_valid()` raises (never returns False) when a refresh is required but fails upstream --
    confirm SsoAuth propagates that failure instead of reporting a successful session."""

    class _FailingRefresher:
        def ensure_valid(self) -> bool:
            raise RuntimeError("aws-sso refresh failed")

    session_calls: list[str] = []

    def session_factory(profile_name: str) -> _FakeSession:
        session_calls.append(profile_name)
        return _FakeSession()

    auth = SsoAuth(
        refresher_factory=lambda profile_name: _FailingRefresher(),
        session_factory=session_factory,
    )

    try:
        auth.ensure_session("broken-profile")
        raise AssertionError("expected RuntimeError to propagate")
    except RuntimeError:
        pass

    assert session_calls == [], "session_factory must not run when the refresh check raises"


def test_sso_auth_construction_requires_collaborator() -> None:
    """DIP pair (pre-implementation-design-review finding #2): construction without collaborators must fail loudly."""
    try:
        SsoAuth()  # type: ignore[call-arg]  # intentional: both args are required, no defaults
        raise AssertionError("expected TypeError: SsoAuth requires both collaborators")
    except TypeError:
        pass

    try:
        SsoAuth(refresher_factory=lambda profile_name: _FakeRefresher(already_valid=True))  # type: ignore[call-arg]
        raise AssertionError("expected TypeError: session_factory is still missing")
    except TypeError:
        pass

    try:
        SsoAuth(session_factory=lambda profile_name: _FakeSession())  # type: ignore[call-arg]
        raise AssertionError("expected TypeError: refresher_factory is still missing")
    except TypeError:
        pass
