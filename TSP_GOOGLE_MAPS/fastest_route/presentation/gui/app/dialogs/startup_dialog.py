"""Input normalization helpers for GUI dialogs."""

from __future__ import annotations

from fastest_route.shared.errors import ValidationError


def normalize_api_key(raw: str) -> str:
    """Normalize a raw API key input into a trimmed, validated string."""
    location = "fastest_route.presentation.gui.app.dialogs.startup_dialog.normalize_api_key"
    if not isinstance(raw, str):
        raise ValidationError(location, "API key must be a string.")
    value = raw.strip()
    if not value:
        raise ValidationError(location, "API key cannot be empty.")
    if any(ch.isspace() for ch in value):
        raise ValidationError(location, "API key must not contain whitespace.")
    return value
