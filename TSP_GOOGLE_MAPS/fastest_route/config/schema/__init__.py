"""Configuration schema definitions for the application."""

from fastest_route.config.schema.app_config import AppConfig
from fastest_route.config.schema.cache import CacheConfig
from fastest_route.config.schema.google_maps import GoogleMapsConfig
from fastest_route.config.schema.http import HttpConfig
from fastest_route.config.schema.logging_config import LoggingConfig
from fastest_route.config.schema.rate_limit import RateLimitConfig
from fastest_route.config.schema.routing import RoutingConfig
from fastest_route.config.schema.ui import UiConfig

__all__: list[str] = [
    "AppConfig",
    "CacheConfig",
    "GoogleMapsConfig",
    "HttpConfig",
    "LoggingConfig",
    "RateLimitConfig",
    "RoutingConfig",
    "UiConfig",
]
