"""Configuration registry facade."""

from fastest_route.config.schema import (
    AppConfig,
    CacheConfig,
    GoogleMapsConfig,
    HttpConfig,
    LoggingConfig,
    RateLimitConfig,
    RoutingConfig,
    UiConfig,
)

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
