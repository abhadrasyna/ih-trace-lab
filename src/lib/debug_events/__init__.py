"""Flattening of `ccl_debug_events` rows shared by investigations."""
from src.lib.debug_events.parser import (
    COMMON_FIELDS,
    EXTRA_FIELDS_BY_EVENTID,
    extract_error_app_version,
    extract_error_client_flags,
    flatten_row,
    parse_eventdata,
    split_clientid,
)

__all__ = [
    "COMMON_FIELDS",
    "EXTRA_FIELDS_BY_EVENTID",
    "extract_error_app_version",
    "extract_error_client_flags",
    "flatten_row",
    "parse_eventdata",
    "split_clientid",
]
