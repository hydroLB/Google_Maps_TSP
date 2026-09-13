"""Logging configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass

from fastest_route.shared.errors import ConfigError


@dataclass(frozen=True)
class LoggingConfig:
    """Hold logging configuration settings."""

    level: str

    def validate(self) -> None:
        """Validate logging level settings."""
        location = "fastest_route.config.registry.LoggingConfig.validate"
        if not self.level.strip():
            raise ConfigError(location, "level must be set.")
