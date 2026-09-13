"""UI configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass

from fastest_route.shared.errors import ConfigError

_MAX_UI_STOPS_FOR_LEGACY_MATRIX = 8


@dataclass(frozen=True)
class UiConfig:
    """Hold UI limits and interaction settings."""

    min_stops: int
    max_stops: int
    autocomplete_min_chars: int
    autocomplete_delay_ms: int
    status_delay_ms: int
    theme_mode: str
    os_theme_poll_seconds: float

    def validate(self) -> None:
        """Validate UI configuration values."""
        location = "fastest_route.config.registry.UiConfig.validate"
        if self.min_stops <= 0:
            raise ConfigError(location, "min_stops must be positive.")
        if self.max_stops < self.min_stops:
            raise ConfigError(location, "max_stops must be greater than or equal to min_stops.")
        if self.max_stops > _MAX_UI_STOPS_FOR_LEGACY_MATRIX:
            raise ConfigError(
                location,
                "max_stops must be 8 or less so stops plus optional endpoints fit the "
                "Distance Matrix API request bound.",
            )
        if self.autocomplete_min_chars <= 0:
            raise ConfigError(location, "autocomplete_min_chars must be positive.")
        if self.autocomplete_delay_ms <= 0:
            raise ConfigError(location, "autocomplete_delay_ms must be positive.")
        if self.status_delay_ms <= 0:
            raise ConfigError(location, "status_delay_ms must be positive.")
        normalized_theme_mode = self.theme_mode.strip().lower()
        if normalized_theme_mode not in {"auto", "system", "light", "dark"}:
            raise ConfigError(location, "theme_mode must be one of: auto, system, light, dark.")
        if self.os_theme_poll_seconds <= 0:
            raise ConfigError(location, "os_theme_poll_seconds must be positive.")
        if self.os_theme_poll_seconds < 0.5:
            raise ConfigError(location, "os_theme_poll_seconds must be at least 0.5 seconds.")
        if self.os_theme_poll_seconds > 60:
            raise ConfigError(location, "os_theme_poll_seconds must be 60 seconds or less.")
