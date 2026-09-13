"""Tk and ttk style application helpers for the GUI theme system."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from tkinter import ttk

from fastest_route.presentation.gui.app.views.theme_support.appearance import (
    detect_system_appearance,
    normalize_theme_mode,
)
from fastest_route.presentation.gui.app.views.theme_support.colors import resolve_theme_color
from fastest_route.presentation.gui.app.views.theme_support.tokens import (
    GuiAppearance,
    GuiThemeTokens,
    ThemeColorRole,
    get_theme_tokens,
    set_current_appearance,
)
from fastest_route.shared.errors import ValidationError


def apply_theme(*, root: tk.Tk, appearance: GuiAppearance) -> None:
    """Configure ttk styles and root defaults for a consistent GUI look and feel."""
    set_current_appearance(appearance=appearance)
    _apply_theme_impl(root=root, tokens=get_theme_tokens(appearance=appearance))


def apply_theme_from_preference(*, root: tk.Tk, preference: str) -> GuiAppearance:
    """Apply a theme based on a user preference of auto, light, or dark."""
    normalized = normalize_theme_mode(preference=preference)
    if normalized == "dark":
        appearance: GuiAppearance = "dark"
    elif normalized == "light":
        appearance = "light"
    else:
        detected = detect_system_appearance()
        appearance = detected if detected is not None else "light"
    apply_theme(root=root, appearance=appearance)
    return appearance


def apply_density_profile(*, root: tk.Tk, compact: bool) -> None:
    """Apply compact or standard spacing and control sizing to ttk styles."""
    location = (
        "fastest_route.presentation.gui.app.views.theme_support.application.apply_density_profile"
    )
    if not root:
        raise ValidationError(location, "root is required.")
    tokens = get_theme_tokens()
    try:
        style = ttk.Style(root)
        section_padding, button_padding, entry_padding, inline_padding, arrow_size = (
            _density_values(tokens=tokens, compact=compact)
        )
        style.configure("App.TLabelframe", padding=section_padding)
        style.configure("Section.Outer.TLabelframe", padding=section_padding)
        style.configure("Primary.TButton", padding=button_padding)
        style.configure("Secondary.TButton", padding=button_padding)
        style.configure("Toolbar.TButton", padding=button_padding)
        style.configure("Default.TButton", padding=button_padding)
        style.configure("Segmented.TButton", padding=button_padding)
        style.configure("App.TEntry", padding=entry_padding)
        style.configure("App.TRadiobutton", padding=inline_padding)
        style.configure("App.TCheckbutton", padding=inline_padding)
        style.configure("App.Vertical.TScrollbar", arrowsize=arrow_size)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to apply density profile.") from exc


def _density_values(
    *, tokens: GuiThemeTokens, compact: bool
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int], int]:
    """Resolve the style padding and sizing values for a density profile."""
    if compact:
        return (
            (tokens.section_padding_x, tokens.compact_section_padding_y),
            (tokens.control_padding_x, tokens.compact_control_padding_y),
            (tokens.inline_gap, max(1, tokens.inline_gap - 3)),
            (max(2, tokens.inline_gap - 2), 0),
            tokens.scrollbar_arrow_size_compact,
        )
    return (
        (tokens.section_padding_x, tokens.section_padding_y),
        (tokens.control_padding_x, tokens.control_padding_y),
        (tokens.inline_gap, tokens.inline_gap - 1),
        (tokens.inline_gap, 0),
        tokens.scrollbar_arrow_size,
    )


def _walk_widgets(*, root: tk.Misc) -> list[tk.Misc]:
    """Walk the widget tree rooted at a Tkinter widget."""
    widgets: list[tk.Misc] = []
    stack: list[tk.Misc] = [root]
    while stack:
        widget = stack.pop()
        widgets.append(widget)
        with suppress(tk.TclError):
            for child in widget.winfo_children():
                if isinstance(child, tk.Misc):
                    stack.append(child)
    return widgets


def _apply_theme_to_tk_widgets(*, root: tk.Tk, tokens: GuiThemeTokens) -> None:
    """Apply theme colors to non-ttk Tk widgets in the widget tree."""
    for widget in _walk_widgets(root=root):
        with suppress(tk.TclError):
            if isinstance(widget, tk.Text):
                _apply_text_widget_theme(widget=widget, tokens=tokens)
            elif isinstance(widget, tk.Listbox):
                _apply_listbox_theme(widget=widget, tokens=tokens)
            elif isinstance(widget, tk.Toplevel):
                _apply_toplevel_theme(widget=widget, tokens=tokens)


def _apply_text_widget_theme(*, widget: tk.Text, tokens: GuiThemeTokens) -> None:
    """Apply token-derived colors to a Tk text widget."""
    widget.configure(
        bg=resolve_theme_color(role="output.background", tokens=tokens),
        fg=resolve_theme_color(role="text.primary", tokens=tokens),
        insertbackground=resolve_theme_color(role="text.primary", tokens=tokens),
        selectbackground=resolve_theme_color(role="selection.background", tokens=tokens),
        selectforeground=resolve_theme_color(role="selection.foreground", tokens=tokens),
        highlightbackground=resolve_theme_color(role="border.subtle", tokens=tokens),
        highlightcolor=resolve_theme_color(role="border.focus", tokens=tokens),
    )


def _apply_listbox_theme(*, widget: tk.Listbox, tokens: GuiThemeTokens) -> None:
    """Apply token-derived colors to a Tk listbox widget."""
    widget.configure(
        bg=resolve_theme_color(role="surface.default", tokens=tokens),
        fg=resolve_theme_color(role="text.primary", tokens=tokens),
        selectbackground=resolve_theme_color(role="selection.background", tokens=tokens),
        selectforeground=resolve_theme_color(role="selection.foreground", tokens=tokens),
        highlightbackground=resolve_theme_color(role="border.subtle", tokens=tokens),
        highlightcolor=resolve_theme_color(role="border.focus", tokens=tokens),
    )


def _apply_toplevel_theme(*, widget: tk.Toplevel, tokens: GuiThemeTokens) -> None:
    """Apply token-derived colors to a Tk toplevel widget."""
    background = resolve_theme_color(role="app.background", tokens=tokens)
    with suppress(tk.TclError):
        if widget.overrideredirect():
            background = resolve_theme_color(role="border.subtle", tokens=tokens)
    widget.configure(background=background)


def _apply_theme_impl(*, root: tk.Tk, tokens: GuiThemeTokens) -> None:
    """Configure ttk styles and apply updates to existing Tk widgets."""
    location = "fastest_route.presentation.gui.app.views.theme_support.application.apply_theme"
    if not root:
        raise ValidationError(location, "root is required.")
    try:
        style = ttk.Style(root)
        _select_ttk_theme(style)
        palette = _theme_palette(tokens=tokens)

        root.configure(background=resolve_theme_color(role="app.background", tokens=tokens))
        root.option_add("*TCombobox*Listbox.font", "TkDefaultFont 10")

        _configure_frame_styles(style=style, tokens=tokens, palette=palette)
        _configure_label_styles(style=style, tokens=tokens, palette=palette)
        _configure_button_styles(style=style, tokens=tokens)
        _configure_input_styles(style=style, tokens=tokens, palette=palette)
        _configure_scrollbar_styles(style=style, tokens=tokens, palette=palette)
        _configure_button_state_maps(style=style, tokens=tokens)
        _configure_misc_style_maps(style=style, tokens=tokens, palette=palette)
        _apply_theme_to_tk_widgets(root=root, tokens=tokens)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to apply GUI theme.") from exc


def _theme_palette(*, tokens: GuiThemeTokens) -> dict[str, str]:
    """Build a small palette of repeatedly used semantic colors for style setup."""
    return {
        "surface_default": resolve_theme_color(role="surface.default", tokens=tokens),
        "surface_subtle": resolve_theme_color(role="surface.subtle", tokens=tokens),
        "surface_inset": resolve_theme_color(role="surface.inset", tokens=tokens),
        "border_subtle": resolve_theme_color(role="border.subtle", tokens=tokens),
        "border_focus": resolve_theme_color(role="border.focus", tokens=tokens),
        "text_primary": resolve_theme_color(role="text.primary", tokens=tokens),
        "text_muted": resolve_theme_color(role="text.muted", tokens=tokens),
        "text_hint": resolve_theme_color(role="text.hint", tokens=tokens),
        "text_empty_state": resolve_theme_color(role="text.empty_state", tokens=tokens),
        "text_disabled": resolve_theme_color(role="text.disabled", tokens=tokens),
    }


def _configure_frame_styles(
    *, style: ttk.Style, tokens: GuiThemeTokens, palette: dict[str, str]
) -> None:
    """Configure ttk frame and labelframe styles for the application shell."""
    style.configure(
        "Page.TFrame",
        background=resolve_theme_color(role="app.background", tokens=tokens),
    )
    style.configure("App.TFrame", background=palette["surface_default"])
    style.configure(
        "Section.Content.TFrame",
        background=palette["surface_inset"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "App.TLabelframe",
        background=palette["surface_default"],
        padding=(tokens.section_padding_x, tokens.section_padding_y),
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "App.TLabelframe.Label",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_heading,
    )
    style.configure(
        "Section.Outer.TLabelframe",
        background=palette["surface_default"],
        padding=(tokens.section_padding_x, tokens.section_padding_y),
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Section.Outer.TLabelframe.Label",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_heading,
    )


def _configure_label_styles(
    *, style: ttk.Style, tokens: GuiThemeTokens, palette: dict[str, str]
) -> None:
    """Configure ttk label styles for headings, body text, hints, and statuses."""
    style.configure(
        "SectionHeading.TLabel",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_heading,
    )
    style.configure(
        "FormLabel.TLabel",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_body,
    )
    style.configure(
        "Body.TLabel",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_body,
    )
    style.configure(
        "Hint.TLabel",
        background=palette["surface_default"],
        foreground=palette["text_hint"],
        font=tokens.font_body,
    )
    style.configure(
        "Muted.TLabel",
        background=palette["surface_default"],
        foreground=palette["text_muted"],
        font=tokens.font_body,
    )
    attribution_foreground = "#FFFFFF" if tokens.app_background.lower() == "#0c1320" else "#1F1F1F"
    style.configure(
        "GoogleMapsAttribution.TLabel",
        background=palette["surface_default"],
        foreground=attribution_foreground,
        font=("TkDefaultFont", 12),
    )
    style.configure(
        "EmptyState.TLabel",
        background=palette["surface_default"],
        foreground=palette["text_empty_state"],
        font=tokens.font_body,
    )
    _configure_status_styles(style=style, tokens=tokens, background=palette["surface_default"])


def _configure_status_styles(*, style: ttk.Style, tokens: GuiThemeTokens, background: str) -> None:
    """Configure semantic status label styles and retained legacy aliases."""
    status_roles: dict[str, ThemeColorRole] = {
        "Status.Text.TLabel": "text.ready",
        "Status.Ready.TLabel": "text.ready",
        "Status.Working.TLabel": "text.working",
        "Status.Success.TLabel": "text.success",
        "Status.Error.TLabel": "text.error",
        "Status.Info.TLabel": "text.ready",
        "Status.Ok.TLabel": "text.success",
        "Status.Warn.TLabel": "text.working",
    }
    for style_name, role in status_roles.items():
        style.configure(
            style_name,
            background=background,
            foreground=resolve_theme_color(role=role, tokens=tokens),
            font=tokens.font_body_bold,
        )


def _configure_button_styles(*, style: ttk.Style, tokens: GuiThemeTokens) -> None:
    """Configure base ttk button styles for primary, secondary, and segmented actions."""
    secondary_fg = resolve_theme_color(role="button.secondary.foreground", tokens=tokens)
    secondary_bg = resolve_theme_color(role="button.secondary.background", tokens=tokens)
    style.configure(
        "Default.TButton",
        padding=(tokens.control_padding_x, tokens.control_padding_y),
        font=tokens.font_body,
        borderwidth=1,
        relief="solid",
        foreground=secondary_fg,
        background=secondary_bg,
    )
    style.configure(
        "Toolbar.TButton",
        padding=(tokens.control_padding_x, tokens.control_padding_y),
        font=tokens.font_body,
        borderwidth=1,
        relief="solid",
        foreground=secondary_fg,
        background=secondary_bg,
    )
    style.configure(
        "Secondary.TButton",
        padding=(tokens.control_padding_x, tokens.control_padding_y),
        font=tokens.font_body,
        borderwidth=1,
        relief="solid",
        foreground=secondary_fg,
        background=secondary_bg,
    )
    style.configure(
        "Primary.TButton",
        padding=(tokens.control_padding_x, tokens.control_padding_y),
        font=tokens.font_body_bold,
        borderwidth=1,
        relief="solid",
        foreground=resolve_theme_color(role="button.primary.foreground", tokens=tokens),
        background=resolve_theme_color(role="button.primary.background", tokens=tokens),
    )
    style.configure(
        "Segmented.TButton",
        padding=(tokens.control_padding_x, tokens.control_padding_y),
        font=tokens.font_body,
        borderwidth=1,
        relief="flat",
        foreground=resolve_theme_color(role="button.segmented.foreground", tokens=tokens),
        background=resolve_theme_color(role="button.segmented.background", tokens=tokens),
    )


def _configure_input_styles(
    *, style: ttk.Style, tokens: GuiThemeTokens, palette: dict[str, str]
) -> None:
    """Configure ttk input controls such as entries, radio buttons, and checkbuttons."""
    style.configure(
        "App.TRadiobutton",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_body,
        padding=(tokens.inline_gap, 0),
    )
    style.configure(
        "Segmented.TRadiobutton",
        background=palette["surface_default"],
        foreground=resolve_theme_color(role="button.segmented.foreground", tokens=tokens),
        font=tokens.font_body,
        borderwidth=1,
        relief="solid",
        padding=(tokens.inline_gap + 1, 2),
    )
    style.configure(
        "App.TCheckbutton",
        background=palette["surface_default"],
        foreground=palette["text_primary"],
        font=tokens.font_body,
        padding=(tokens.inline_gap, 0),
    )
    style.configure(
        "App.TEntry",
        padding=(tokens.inline_gap, tokens.inline_gap - 1),
        foreground=palette["text_primary"],
        fieldbackground=resolve_theme_color(role="input.background", tokens=tokens),
        bordercolor=resolve_theme_color(role="input.border", tokens=tokens),
        insertcolor=palette["text_primary"],
    )


def _configure_scrollbar_styles(
    *, style: ttk.Style, tokens: GuiThemeTokens, palette: dict[str, str]
) -> None:
    """Configure the themed vertical scrollbar used by the output panel."""
    style.configure(
        "App.Vertical.TScrollbar",
        background=resolve_theme_color(role="scrollbar.thumb", tokens=tokens),
        troughcolor=resolve_theme_color(role="scrollbar.track", tokens=tokens),
        bordercolor=palette["border_subtle"],
        lightcolor=palette["surface_subtle"],
        darkcolor=palette["surface_subtle"],
        arrowcolor=palette["text_muted"],
        arrowsize=tokens.scrollbar_arrow_size,
        relief="flat",
    )


def _configure_misc_style_maps(
    *, style: ttk.Style, tokens: GuiThemeTokens, palette: dict[str, str]
) -> None:
    """Configure ttk state maps for entries, option controls, and scrollbars."""
    with suppress(tk.TclError):
        style.map(
            "App.TEntry",
            fieldbackground=[
                ("disabled", resolve_theme_color(role="input.background_disabled", tokens=tokens)),
                ("readonly", palette["surface_subtle"]),
                ("!disabled", resolve_theme_color(role="input.background", tokens=tokens)),
            ],
            foreground=[
                ("disabled", palette["text_disabled"]),
                ("!disabled", palette["text_primary"]),
            ],
            bordercolor=[
                ("focus", palette["border_focus"]),
                ("disabled", palette["border_subtle"]),
                ("!disabled", resolve_theme_color(role="input.border", tokens=tokens)),
            ],
        )
    with suppress(tk.TclError):
        style.map(
            "App.TRadiobutton",
            foreground=[
                ("disabled", palette["text_disabled"]),
                ("!disabled", palette["text_primary"]),
            ],
            background=[
                ("active", palette["surface_subtle"]),
                ("!disabled", palette["surface_default"]),
            ],
        )
    with suppress(tk.TclError):
        style.map(
            "Segmented.TRadiobutton",
            foreground=[
                ("disabled", palette["text_disabled"]),
                (
                    "selected",
                    resolve_theme_color(role="button.segmented.foreground_selected", tokens=tokens),
                ),
                (
                    "!disabled",
                    resolve_theme_color(role="button.segmented.foreground", tokens=tokens),
                ),
            ],
            background=[
                ("disabled", resolve_theme_color(role="surface.disabled", tokens=tokens)),
                (
                    "selected",
                    resolve_theme_color(role="button.segmented.background_selected", tokens=tokens),
                ),
                (
                    "active",
                    resolve_theme_color(role="button.segmented.background_hover", tokens=tokens),
                ),
                (
                    "!disabled",
                    resolve_theme_color(role="button.segmented.background", tokens=tokens),
                ),
            ],
        )
    with suppress(tk.TclError):
        style.map(
            "App.TCheckbutton",
            foreground=[
                ("disabled", palette["text_disabled"]),
                ("!disabled", palette["text_primary"]),
            ],
            background=[
                ("active", palette["surface_subtle"]),
                ("!disabled", palette["surface_default"]),
            ],
        )
    with suppress(tk.TclError):
        style.map(
            "App.Vertical.TScrollbar",
            background=[
                ("active", resolve_theme_color(role="scrollbar.thumb_hover", tokens=tokens)),
                ("!active", resolve_theme_color(role="scrollbar.thumb", tokens=tokens)),
            ],
        )


def _configure_button_state_maps(*, style: ttk.Style, tokens: GuiThemeTokens) -> None:
    """Configure state maps for all semantic button styles."""
    _map_button_states(
        style=style,
        style_name="Primary.TButton",
        tokens=tokens,
        base_bg_role="button.primary.background",
        hover_bg_role="button.primary.background_hover",
        active_bg_role="button.primary.background_active",
        fg_role="button.primary.foreground",
    )
    _map_button_states(
        style=style,
        style_name="Default.TButton",
        tokens=tokens,
        base_bg_role="button.secondary.background",
        hover_bg_role="button.secondary.background_hover",
        active_bg_role="button.secondary.background_active",
        fg_role="button.secondary.foreground",
    )
    _map_button_states(
        style=style,
        style_name="Toolbar.TButton",
        tokens=tokens,
        base_bg_role="button.secondary.background",
        hover_bg_role="button.secondary.background_hover",
        active_bg_role="button.secondary.background_active",
        fg_role="button.secondary.foreground",
    )
    _map_button_states(
        style=style,
        style_name="Secondary.TButton",
        tokens=tokens,
        base_bg_role="button.secondary.background",
        hover_bg_role="button.secondary.background_hover",
        active_bg_role="button.secondary.background_active",
        fg_role="button.secondary.foreground",
    )
    _map_button_states(
        style=style,
        style_name="Segmented.TButton",
        tokens=tokens,
        base_bg_role="button.segmented.background",
        hover_bg_role="button.segmented.background_hover",
        active_bg_role="button.segmented.background_active",
        fg_role="button.segmented.foreground",
    )


def _map_button_states(
    *,
    style: ttk.Style,
    style_name: str,
    tokens: GuiThemeTokens,
    base_bg_role: ThemeColorRole,
    hover_bg_role: ThemeColorRole,
    active_bg_role: ThemeColorRole,
    fg_role: ThemeColorRole,
) -> None:
    """Apply a complete state map for a single button style."""
    with suppress(tk.TclError):
        style.map(
            style_name,
            foreground=[
                ("disabled", resolve_theme_color(role="text.disabled", tokens=tokens)),
                ("!disabled", resolve_theme_color(role=fg_role, tokens=tokens)),
            ],
            background=[
                ("disabled", resolve_theme_color(role="surface.disabled", tokens=tokens)),
                ("pressed", resolve_theme_color(role=active_bg_role, tokens=tokens)),
                ("active", resolve_theme_color(role=hover_bg_role, tokens=tokens)),
                ("!disabled", resolve_theme_color(role=base_bg_role, tokens=tokens)),
            ],
            bordercolor=[
                ("focus", resolve_theme_color(role="border.focus", tokens=tokens)),
                ("disabled", resolve_theme_color(role="border.subtle", tokens=tokens)),
                ("!disabled", resolve_theme_color(role="border.strong", tokens=tokens)),
            ],
            lightcolor=[
                ("focus", resolve_theme_color(role="border.focus", tokens=tokens)),
                ("!disabled", resolve_theme_color(role="border.strong", tokens=tokens)),
            ],
            darkcolor=[
                ("focus", resolve_theme_color(role="border.focus", tokens=tokens)),
                ("!disabled", resolve_theme_color(role="border.strong", tokens=tokens)),
            ],
        )


def _select_ttk_theme(style: ttk.Style) -> None:
    """Select a theme that honors colors, avoiding platform themes such as macOS Aqua."""
    try:
        available = {name.lower(): name for name in style.theme_names()}
        current = style.theme_use()
        for candidate in ("clam", "alt", "default", "classic", "aqua"):
            name = available.get(candidate)
            if name is None:
                continue
            if current.lower() == candidate:
                return
            try:
                style.theme_use(name)
                return
            except tk.TclError:
                continue
    except tk.TclError:
        return
