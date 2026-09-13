"""Semantic GUI color and density helpers built on top of theme tokens."""

from __future__ import annotations

from fastest_route.presentation.gui.app.views.theme_support.tokens import (
    GuiAppearance,
    GuiThemeTokens,
    ThemeColorRole,
    get_theme_tokens,
)
from fastest_route.shared.errors import ValidationError


def resolve_theme_color(
    *,
    role: ThemeColorRole,
    appearance: GuiAppearance | None = None,
    tokens: GuiThemeTokens | None = None,
) -> str:
    """Resolve a semantic color role to a concrete hex value."""
    location = "fastest_route.presentation.gui.app.views.theme_support.colors.resolve_theme_color"
    active_tokens = tokens if tokens is not None else get_theme_tokens(appearance=appearance)
    value = _role_map(tokens=active_tokens).get(role)
    if value is None:
        raise ValidationError(location, f"Unknown theme color role: {role}")
    return value


def resolve_status_style(*, status_text: str) -> str:
    """Map status text into a semantic ttk label style."""
    normalized = status_text.strip().lower()
    if not normalized:
        return "Status.Ready.TLabel"
    if "error" in normalized or "fail" in normalized or "attention" in normalized:
        return "Status.Error.TLabel"
    if "ready" in normalized or "idle" in normalized:
        return "Status.Ready.TLabel"
    if "success" in normalized or "complete" in normalized:
        return "Status.Success.TLabel"
    if "working" in normalized or "calculating" in normalized or "cancel" in normalized:
        return "Status.Working.TLabel"
    return "Status.Ready.TLabel"


def is_compact_window_size(
    *, width: int, height: int, tokens: GuiThemeTokens | None = None
) -> bool:
    """Determine whether a window size should use compact spacing and control sizing."""
    active_tokens = tokens if tokens is not None else get_theme_tokens()
    return (
        width <= active_tokens.compact_threshold_width
        or height <= active_tokens.compact_threshold_height
    )


def _role_map(*, tokens: GuiThemeTokens) -> dict[ThemeColorRole, str]:
    """Build the semantic role map for a specific token set."""
    return {
        "app.background": tokens.app_background,
        "surface.default": tokens.surface_background,
        "surface.subtle": tokens.surface_subtle,
        "surface.inset": tokens.surface_inset,
        "surface.disabled": tokens.surface_disabled,
        "border.subtle": tokens.border_subtle,
        "border.strong": tokens.border_strong,
        "border.focus": tokens.border_focus,
        "text.primary": tokens.text_primary,
        "text.muted": tokens.text_muted,
        "text.hint": tokens.text_hint,
        "text.empty_state": tokens.text_empty_state,
        "text.disabled": tokens.text_disabled,
        "text.ready": tokens.text_ready,
        "text.working": tokens.text_working,
        "text.success": tokens.text_success,
        "text.error": tokens.text_error,
        "button.primary.background": tokens.primary_bg,
        "button.primary.background_hover": tokens.primary_bg_hover,
        "button.primary.background_active": tokens.primary_bg_active,
        "button.primary.foreground": tokens.primary_fg,
        "button.secondary.background": tokens.secondary_bg,
        "button.secondary.background_hover": tokens.secondary_bg_hover,
        "button.secondary.background_active": tokens.secondary_bg_active,
        "button.secondary.foreground": tokens.secondary_fg,
        "button.segmented.background": tokens.segmented_bg,
        "button.segmented.background_hover": tokens.segmented_bg_hover,
        "button.segmented.background_active": tokens.segmented_bg_active,
        "button.segmented.background_selected": tokens.segmented_bg_selected,
        "button.segmented.foreground": tokens.segmented_fg,
        "button.segmented.foreground_selected": tokens.segmented_fg_selected,
        "input.background": tokens.input_bg,
        "input.background_disabled": tokens.input_bg_disabled,
        "input.border": tokens.input_border,
        "output.background": tokens.output_bg,
        "selection.background": tokens.selection_bg,
        "selection.foreground": tokens.selection_fg,
        "scrollbar.track": tokens.scrollbar_track,
        "scrollbar.thumb": tokens.scrollbar_thumb,
        "scrollbar.thumb_hover": tokens.scrollbar_thumb_hover,
    }
