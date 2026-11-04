"""Exception hierarchy for the usage tracking pipeline."""
from __future__ import annotations


class UsageTrackingError(Exception):
    """Base class for every expected usage tracking failure."""


class RosterError(UsageTrackingError):
    """The tracked-household roster is missing or malformed."""


class AthenaSourceError(UsageTrackingError):
    """An Athena export is missing or malformed, or a live Athena call failed."""


class LightstepSourceError(UsageTrackingError):
    """A Lightstep export is missing or malformed, or a live Lightstep call failed."""


class MergeError(UsageTrackingError):
    """A row handed to the merge step is malformed."""
