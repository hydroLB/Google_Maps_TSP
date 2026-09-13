"""UI configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_float, get_int, get_str
from fastest_route.config.registry import UiConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_ui_config(*, ui_section: Mapping[str, object], location: str) -> UiConfig:
    """Build a UiConfig from the TOML ui section."""
    return UiConfig(
        min_stops=get_int(ui_section, "min_stops", 3, location),
        max_stops=get_int(ui_section, "max_stops", 7, location),
        autocomplete_min_chars=get_int(ui_section, "autocomplete_min_chars", 3, location),
        autocomplete_delay_ms=get_int(ui_section, "autocomplete_delay_ms", 300, location),
        status_delay_ms=get_int(ui_section, "status_delay_ms", 600, location),
        theme_mode=get_str(ui_section, "theme_mode", "auto", location),
        os_theme_poll_seconds=get_float(ui_section, "os_theme_poll_seconds", 2.0, location),
    )
