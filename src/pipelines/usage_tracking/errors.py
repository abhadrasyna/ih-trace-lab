"""Exception hierarchy for the usage tracking pipeline."""
from __future__ import annotations


class UsageTrackingError(Exception):
    """Base class for every expected usage tracking failure."""


class RosterError(UsageTrackingError):
    """The tracked-household roster is missing or malformed."""
