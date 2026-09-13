"""Top-level application configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ConfigError

if TYPE_CHECKING:
    from fastest_route.config.schema.cache import CacheConfig
    from fastest_route.config.schema.google_maps import GoogleMapsConfig
    from fastest_route.config.schema.http import HttpConfig
    from fastest_route.config.schema.logging_config import LoggingConfig
    from fastest_route.config.schema.rate_limit import RateLimitConfig
    from fastest_route.config.schema.routing import RoutingConfig
    from fastest_route.config.schema.ui import UiConfig


@dataclass(frozen=True)
class AppConfig:
    """Hold the full application configuration registry."""

    environment: str
    google_maps: GoogleMapsConfig
    cache: CacheConfig
    routing: RoutingConfig
    http: HttpConfig
    rate_limit: RateLimitConfig
    logging: LoggingConfig
    ui: UiConfig

    def validate(self) -> None:
        """Validate nested configuration values."""
        location = "fastest_route.config.registry.AppConfig.validate"
        if not self.environment.strip():
            raise ConfigError(location, "environment must be set.")
        allow_empty_key = self.environment.lower() in {"test", "ci", "dev", "local"}
        self.google_maps.validate(allow_empty_key=allow_empty_key)
        self.cache.validate()
        self.routing.validate()
        self.http.validate()
        self.rate_limit.validate()
        self.logging.validate()
        self.ui.validate()
