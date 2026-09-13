from __future__ import annotations

import pytest

from fastest_route.presentation.gui.app.dialogs.startup_dialog import normalize_api_key
from fastest_route.shared.errors import ValidationError


def test_normalize_api_key_strips() -> None:
    """Prevents subtle failures when users paste keys with surrounding whitespace."""
    assert normalize_api_key("  abc123  ") == "abc123"


def test_normalize_api_key_rejects_empty() -> None:
    """Startup should not proceed with an empty key in Google mode."""
    with pytest.raises(ValidationError):
        normalize_api_key("   ")


def test_normalize_api_key_rejects_internal_whitespace() -> None:
    """Prevents accidental whitespace from causing confusing auth failures."""
    with pytest.raises(ValidationError):
        normalize_api_key("abc 123")
