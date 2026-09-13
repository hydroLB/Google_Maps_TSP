"""Rate limiting configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass

from fastest_route.shared.errors import ConfigError


@dataclass(frozen=True)
class RateLimitConfig:
    """Hold rate limiting configuration."""

    requests_per_second: float
    burst: int
    max_wait_seconds: float

    def validate(self) -> None:
        """Validate rate limit settings."""
        location = "fastest_route.config.registry.RateLimitConfig.validate"
        if self.requests_per_second <= 0:
            raise ConfigError(location, "requests_per_second must be positive.")
        if self.burst <= 0:
            raise ConfigError(location, "burst must be positive.")
        if self.max_wait_seconds <= 0:
            raise ConfigError(location, "max_wait_seconds must be positive.")
