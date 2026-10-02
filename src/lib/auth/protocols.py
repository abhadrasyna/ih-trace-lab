"""Protocol skeleton for AWS SSO profile-session auth, generalized from `athena_runner.sso_auth`.

See `docs/plan/src-lib-migration/auth-lib-migration/stories.md` AUM-1 for the full spec this implements.
`functional-code-taxonomy` named `auth` as a shared `src/lib/*` module but deliberately deferred its `Protocol`
until a real consumer needed it; this story is that consumer, generalizing `athena_runner.sso_auth`'s proven
`SsoCredentialRefresher.ensure_valid()` shape (landed via `athena-lib-integration`) rather than inventing an
auth interface from nothing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import boto3


@runtime_checkable
class AuthProtocol(Protocol):
    """DIP seam: AWS SSO profile-session auth, for non-Athena consumers needing an authenticated `boto3.Session`."""

    def ensure_session(self, profile_name: str) -> "boto3.Session":
        ...

    def refresh_if_expired(self, profile_name: str) -> bool:
        """Return True if a refresh was actually performed; False if the session was already valid."""
        ...
