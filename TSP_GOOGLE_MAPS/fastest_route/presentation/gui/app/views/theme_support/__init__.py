"""Internal helpers for GUI theme tokens, appearance detection, and style application."""

from fastest_route.presentation.gui.app.views.theme_support.appearance import (
    detect_system_appearance,
    normalize_theme_mode,
    should_follow_system_theme,
)
from fastest_route.presentation.gui.app.views.theme_support.application import (
    apply_density_profile,
    apply_theme,
    apply_theme_from_preference,
)
from fastest_route.presentation.gui.app.views.theme_support.colors import (
    is_compact_window_size,
    resolve_status_style,
    resolve_theme_color,
)
from fastest_route.presentation.gui.app.views.theme_support.tokens import (
    GuiAppearance,
    GuiThemeMode,
    GuiThemeTokens,
    ThemeColorRole,
    get_theme_tokens,
)

__all__ = [
    "GuiAppearance",
    "GuiThemeMode",
    "GuiThemeTokens",
    "ThemeColorRole",
    "apply_density_profile",
    "apply_theme",
    "apply_theme_from_preference",
    "detect_system_appearance",
    "get_theme_tokens",
    "is_compact_window_size",
    "normalize_theme_mode",
    "resolve_status_style",
    "resolve_theme_color",
    "should_follow_system_theme",
]
