"""Protocol skeleton for curl-to-Python conversion.

No prior ``src/lib``-worthy converter exists to replace: FCT-1's audit cited a
generic responsibility for ``src/lib/curl_to_python/`` but named no specific
file, and re-deriving the actual shape from
``mtn-network-traffic/scripts/curl_timer/`` found only curl-*execution*
tooling (it shells out to the real ``curl`` binary for timing), never a
curl-command-to-Python-``requests``-text generator. See
``docs/plan/src-lib-migration/curl-to-python-lib-migration/stories.md``'s
"CPM-1 finding" subsection for the full citation trail.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CurlConverterProtocol(Protocol):
    """Converts a captured curl command into Python ``requests`` source text.

    Built ahead of a proven-duplication trigger, per this epic's explicit
    authorization: the confirmed real consumer is a manual, ad hoc workflow
    (HAR-driven timing/latency investigation) rather than a pipeline that
    already calls an existing implementation.
    """

    def convert(self, curl_command: str) -> str:
        """Return Python ``requests``-call source text for ``curl_command``.

        Must not execute the request described by ``curl_command`` — this is
        text/AST generation only, never ``exec``/``eval``, never a network
        call made during conversion.
        """
        ...
