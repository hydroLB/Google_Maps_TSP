"""Error formatting helpers for user-facing GUI dialogs."""

from __future__ import annotations


def strip_location_prefix(message: str) -> str:
    """Remove the "location: " prefix from an error message for user-facing dialogs."""
    if not isinstance(message, str):
        return str(message)
    if ": " not in message:
        return message
    return message.split(": ", 1)[1]
