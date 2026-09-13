from __future__ import annotations

import pytest

from fastest_route.presentation.gui.app.views.theme import (
    normalize_theme_mode,
    resolve_status_style,
    resolve_theme_color,
    should_follow_system_theme,
)
from fastest_route.shared.errors import ValidationError


def test_normalize_theme_mode_supports_auto_and_system_alias() -> None:
    """Config compatibility should remain stable while auto mode becomes primary."""
    assert normalize_theme_mode(preference="auto") == "auto"
    assert normalize_theme_mode(preference="system") == "auto"
    assert normalize_theme_mode(preference="dark") == "dark"
    assert normalize_theme_mode(preference="light") == "light"


def test_should_follow_system_theme_respects_mode() -> None:
    """OS polling should run only when using auto mode."""
    assert should_follow_system_theme(preference="auto") is True
    assert should_follow_system_theme(preference="system") is True
    assert should_follow_system_theme(preference="light") is False
    assert should_follow_system_theme(preference="dark") is False


def test_resolve_status_style_maps_semantic_status_words() -> None:
    """UI state coloring must follow status meaning consistently."""
    assert resolve_status_style(status_text="Ready") == "Status.Ready.TLabel"
    assert resolve_status_style(status_text="Calculating") == "Status.Working.TLabel"
    assert resolve_status_style(status_text="Needs attention") == "Status.Error.TLabel"


def test_resolve_theme_color_rejects_unknown_role() -> None:
    """Invalid role lookups should fail fast with actionable diagnostics."""
    with pytest.raises(ValidationError):
        resolve_theme_color(role="not-a-role")  # type: ignore[arg-type]
