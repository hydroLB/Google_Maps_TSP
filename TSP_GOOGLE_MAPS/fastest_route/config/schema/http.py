"""HTTP configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class HttpConfig:
    """Hold HTTP timeout and retry settings."""

    timeout_seconds: float
    retry_max_attempts: int
    retry_base_delay_seconds: float
    retry_max_delay_seconds: float
    retry_jitter_ratio: float
    retry_statuses: Sequence[int]

    def validate(self) -> None:
        """Validate HTTP configuration values."""
        location = "fastest_route.config.registry.HttpConfig.validate"
        if self.timeout_seconds <= 0:
            raise ConfigError(location, "timeout_seconds must be positive.")
        if self.retry_max_attempts <= 0:
            raise ConfigError(location, "retry_max_attempts must be positive.")
        if self.retry_base_delay_seconds <= 0:
            raise ConfigError(location, "retry_base_delay_seconds must be positive.")
        if self.retry_max_delay_seconds <= 0:
            raise ConfigError(location, "retry_max_delay_seconds must be positive.")
        if not 0 <= self.retry_jitter_ratio <= 1:
            raise ConfigError(location, "retry_jitter_ratio must be between 0 and 1.")
