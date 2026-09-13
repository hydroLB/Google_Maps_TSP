"""Public GUI theme facade exposing tokens, color helpers, appearance detection, and style application."""

from fastest_route.presentation.gui.app.views.theme_support import (
    GuiAppearance,
    GuiThemeMode,
    GuiThemeTokens,
    ThemeColorRole,
    apply_density_profile,
    apply_theme,
    apply_theme_from_preference,
    detect_system_appearance,
    get_theme_tokens,
    is_compact_window_size,
    normalize_theme_mode,
    resolve_status_style,
    resolve_theme_color,
    should_follow_system_theme,
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
