"""Theme token definitions and appearance-scoped token access for the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GuiAppearance = Literal["light", "dark"]
GuiThemeMode = Literal["auto", "light", "dark"]
ThemeColorRole = Literal[
    "app.background",
    "surface.default",
    "surface.subtle",
    "surface.inset",
    "surface.disabled",
    "border.subtle",
    "border.strong",
    "border.focus",
    "text.primary",
    "text.muted",
    "text.hint",
    "text.empty_state",
    "text.disabled",
    "text.ready",
    "text.working",
    "text.success",
    "text.error",
    "button.primary.background",
    "button.primary.background_hover",
    "button.primary.background_active",
    "button.primary.foreground",
    "button.secondary.background",
    "button.secondary.background_hover",
    "button.secondary.background_active",
    "button.secondary.foreground",
    "button.segmented.background",
    "button.segmented.background_hover",
    "button.segmented.background_active",
    "button.segmented.background_selected",
    "button.segmented.foreground",
    "button.segmented.foreground_selected",
    "input.background",
    "input.background_disabled",
    "input.border",
    "output.background",
    "selection.background",
    "selection.foreground",
    "scrollbar.track",
    "scrollbar.thumb",
    "scrollbar.thumb_hover",
]


@dataclass(frozen=True, slots=True)
class GuiThemeTokens:
    """Store design tokens used by GUI layout and style configuration."""

    window_padding_x: int = 18
    window_padding_y: int = 16
    section_padding_x: int = 12
    section_padding_y: int = 10
    compact_section_padding_y: int = 8
    row_spacing: int = 6
    compact_row_spacing: int = 4
    group_spacing: int = 10
    control_spacing: int = 8
    control_padding_x: int = 10
    control_padding_y: int = 6
    compact_control_padding_y: int = 4
    inline_gap: int = 6
    field_label_width: int = 11
    status_label_width: int = 14
    button_width_primary: int = 17
    button_width_secondary: int = 14
    compact_button_width_primary: int = 15
    compact_button_width_secondary: int = 12
    entry_width_key: int = 58
    entry_width_key_compact: int = 50
    entry_width_standard: int = 46
    entry_width_standard_compact: int = 38
    window_width: int = 1020
    window_height: int = 760
    window_min_width: int = 780
    window_min_height: int = 560
    compact_threshold_width: int = 930
    compact_threshold_height: int = 650
    output_height_rows: int = 13
    compact_output_height_rows: int = 9
    output_width_chars: int = 78
    font_body: tuple[str, int] = ("TkDefaultFont", 10)
    font_body_bold: tuple[str, int, str] = ("TkDefaultFont", 10, "bold")
    font_heading: tuple[str, int, str] = ("TkDefaultFont", 10, "bold")
    app_background: str = "#edf2f7"
    surface_background: str = "#ffffff"
    surface_subtle: str = "#f6f8fb"
    surface_inset: str = "#f9fbfd"
    surface_disabled: str = "#edf2f8"
    border_subtle: str = "#d3dce8"
    border_strong: str = "#97a6ba"
    border_focus: str = "#5f88bd"
    text_primary: str = "#1f2937"
    text_muted: str = "#5f6b7c"
    text_hint: str = "#697588"
    text_empty_state: str = "#667389"
    text_disabled: str = "#7d8796"
    text_ready: str = "#1f4f86"
    text_working: str = "#805d0f"
    text_success: str = "#1f7249"
    text_error: str = "#8e2323"
    primary_bg: str = "#2f68b1"
    primary_bg_hover: str = "#2a5d9f"
    primary_bg_active: str = "#234f88"
    primary_fg: str = "#ffffff"
    secondary_bg: str = "#f3f7fc"
    secondary_bg_hover: str = "#e7eef7"
    secondary_bg_active: str = "#dce6f3"
    secondary_fg: str = "#2b3b4f"
    segmented_bg: str = "#eef3f9"
    segmented_bg_hover: str = "#e3ebf6"
    segmented_bg_active: str = "#d7e3f3"
    segmented_bg_selected: str = "#ccdcef"
    segmented_fg: str = "#2b3d53"
    segmented_fg_selected: str = "#1f2d3d"
    input_bg: str = "#ffffff"
    input_bg_disabled: str = "#eef3f8"
    input_border: str = "#c9d4e1"
    output_bg: str = "#f8fbff"
    selection_bg: str = "#2f68b1"
    selection_fg: str = "#ffffff"
    scrollbar_track: str = "#edf3fa"
    scrollbar_thumb: str = "#c0cbdb"
    scrollbar_thumb_hover: str = "#aebacd"
    scrollbar_arrow_size: int = 11
    scrollbar_arrow_size_compact: int = 9


_LIGHT_TOKENS = GuiThemeTokens()
_DARK_TOKENS = GuiThemeTokens(
    app_background="#0c1320",
    surface_background="#101b2d",
    surface_subtle="#152237",
    surface_inset="#0f192a",
    surface_disabled="#0e1726",
    border_subtle="#2a3a51",
    border_strong="#4b5f7c",
    border_focus="#6d96cc",
    text_primary="#e8eef7",
    text_muted="#aab5c6",
    text_hint="#9dabc0",
    text_empty_state="#9ba9bf",
    text_disabled="#758295",
    text_ready="#84b7ff",
    text_working="#f0c566",
    text_success="#62d4a5",
    text_error="#ff9494",
    primary_bg="#3a72c2",
    primary_bg_hover="#3468b1",
    primary_bg_active="#2c5897",
    primary_fg="#ffffff",
    secondary_bg="#1a2940",
    secondary_bg_hover="#1f3150",
    secondary_bg_active="#24395e",
    secondary_fg="#e8eef7",
    segmented_bg="#1b2a41",
    segmented_bg_hover="#213350",
    segmented_bg_active="#274066",
    segmented_bg_selected="#33527e",
    segmented_fg="#dce8f8",
    segmented_fg_selected="#ffffff",
    input_bg="#101b2d",
    input_bg_disabled="#0d1626",
    input_border="#3f5674",
    output_bg="#0e1829",
    selection_bg="#3a72c2",
    selection_fg="#ffffff",
    scrollbar_track="#142137",
    scrollbar_thumb="#415675",
    scrollbar_thumb_hover="#4f6790",
)
_CURRENT_APPEARANCE: GuiAppearance = "light"


def get_theme_tokens(*, appearance: GuiAppearance | None = None) -> GuiThemeTokens:
    """Return the singleton token set for GUI layout and style values."""
    active_appearance = _CURRENT_APPEARANCE if appearance is None else appearance
    return _DARK_TOKENS if active_appearance == "dark" else _LIGHT_TOKENS


def set_current_appearance(*, appearance: GuiAppearance) -> None:
    """Update the process-wide appearance used by default token lookups."""
    global _CURRENT_APPEARANCE  # noqa: PLW0603
    _CURRENT_APPEARANCE = appearance
