"""Re-export of the debug-event parser, which now lives in `src/lib/debug_events/`."""
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.debug_events.parser import *  # noqa: F401,F403
from src.lib.debug_events.parser import (  # noqa: F401
    COMMON_FIELDS,
    EXTRA_FIELDS_BY_EVENTID,
    _EXTRACTORS,
    flatten_row,
    parse_eventdata,
    split_clientid,
)
