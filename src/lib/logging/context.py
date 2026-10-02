"""FCID (flow-correlation-id) `contextvars` propagation + auto-injecting log filter.

Scope note: the archived `docs/archive/flow-correlation-id-logging` story (FCID-1) fully specifies this design
(format, generation point, propagation mechanism, log-line shape) but explicitly deferred implementing
`src/lib/logging/` to "a future implementing story" that, as of this writing, no `docs/plan/` task yet owns.
`athena-lib-integration`'s ALI-5 (`src/lib/athena/batch.py`) structurally depends on FCID surviving a
`ThreadPoolExecutor` boundary to satisfy its own locked-in spec and test list, so this module implements only
the minimal slice FCID-1 already fully specified with no open questions: the `ContextVar` + `bind_fcid`/
`current_fcid` pair, and the auto-injecting `logging.Filter`. It deliberately does NOT implement
`redact_params` or wire `%(fcid)s` into any project-wide `setup_logging()` formatter -- those remain future
work for whichever session picks up the deferred FCID implementation task in full.
"""
from __future__ import annotations

import contextvars
import logging

_fcid_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("fcid", default=None)


def bind_fcid(fcid: str) -> None:
    """Binds `fcid` for the current `contextvars` context.

    Call once per run/invocation at an entry point; never re-bind from inside an adapter or downstream helper.
    """
    _fcid_var.set(fcid)


def current_fcid() -> str | None:
    """Returns the FCID bound in the current `contextvars` context, or `None` if none has been bound."""
    return _fcid_var.get()


class FcidLogFilter(logging.Filter):
    """Injects `record.fcid` from `current_fcid()` into every log record passing through it.

    Filters are only consulted for records logged **directly** on the logger (or handler) they're attached to --
    a filter attached to a parent/root logger is NOT consulted for records originating on a child logger before
    those records propagate up to the parent's handlers (see the stdlib `logging.Filterer`/`Logger.filter`
    semantics). Attaching this filter to one specific module logger (as `batch.py` does, for its own log calls)
    is correct and sufficient for that module's own records. A future caller wanting `record.fcid` guaranteed on
    *every* record project-wide (e.g. once `setup_logging()` wires `%(fcid)s` into a shared formatter) must
    attach this filter to the relevant **handlers** instead, not to the root logger, or every record from a
    child logger will fail with "Formatting field not found" once a formatter references `%(fcid)s`.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.fcid = current_fcid() or "no-fcid"
        return True
