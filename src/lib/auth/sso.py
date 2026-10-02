"""Concrete `AuthProtocol` implementer delegating to `athena_runner.sso_auth`-shaped collaborators.

See `docs/plan/src-lib-migration/auth-lib-migration/stories.md` AUM-2.

`athena_runner.sso_auth.SsoCredentialRefresher` binds one AWS profile at construction time and
exposes a no-arg `ensure_valid() -> bool`, but `AuthProtocol` takes `profile_name` per call so one
`SsoAuth` instance can serve multiple profiles. `SsoAuth` bridges that mismatch with a
constructor-injected *factory* (`profile_name -> refresher`) rather than a single bound
collaborator -- it never constructs `SsoCredentialRefresher`, `boto3.Session`, or any AWS client
itself (DIP): all SSO-refresh and session-construction logic stays with the injected collaborators.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable

if TYPE_CHECKING:
    import boto3


@runtime_checkable
class _RefresherLike(Protocol):
    """Structural shape `athena_runner.sso_auth.SsoCredentialRefresher` satisfies."""

    def ensure_valid(self) -> bool:
        ...


RefresherFactory = Callable[[str], _RefresherLike]
SessionFactory = Callable[[str], "boto3.Session"]


class SsoAuth:
    """`AuthProtocol` implementer: delegates SSO refresh and session construction to injected collaborators."""

    def __init__(self, refresher_factory: RefresherFactory, session_factory: SessionFactory) -> None:
        """Initializes the implementer.

        Args:
            refresher_factory: Given a profile name, returns an `ensure_valid()`-shaped collaborator
                (e.g. `athena_runner.sso_auth.SsoCredentialRefresher`) for that profile.
            session_factory: Given a profile name, returns a `boto3.Session` for it. Called only
                after a refresh check, never constructed inline here.
        """
        self._refresher_factory = refresher_factory
        self._session_factory = session_factory

    def refresh_if_expired(self, profile_name: str) -> bool:
        """Returns True if a refresh was actually performed; False if the session was already valid.

        Pass-through of `athena_runner.sso_auth.SsoCredentialRefresher.ensure_valid()`'s own contract:
        that collaborator returns True when credentials were already valid, False when a refresh was
        required and succeeded, and *raises* (rather than returning False) when a refresh is required
        but fails. This method does not catch that exception -- a failed refresh must propagate to the
        caller, never be silently reported as success.
        """
        was_already_valid = self._refresher_factory(profile_name).ensure_valid()
        return not was_already_valid

    def ensure_session(self, profile_name: str) -> "boto3.Session":
        self.refresh_if_expired(profile_name)
        return self._session_factory(profile_name)
