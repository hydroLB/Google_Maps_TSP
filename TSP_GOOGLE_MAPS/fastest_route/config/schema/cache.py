"""Cache configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class CacheConfig:
    """Hold cache sizes and disk cache path settings."""

    disk_path: Path
    geocode_disk_path: Path | None
    route_cache_size: int
    disk_cache_ttl_seconds: int
    geocode_cache_size: int
    geocode_disk_cache_ttl_seconds: int

    def validate(self) -> None:
        """Validate cache settings and sizes."""
        location = "fastest_route.config.registry.CacheConfig.validate"
        if self.route_cache_size <= 0:
            raise ConfigError(location, "route_cache_size must be positive.")
        if self.disk_cache_ttl_seconds <= 0:
            raise ConfigError(location, "disk_cache_ttl_seconds must be positive.")
        if not str(self.disk_path).strip():
            raise ConfigError(location, "disk_path must be set.")
        if self.geocode_cache_size <= 0:
            raise ConfigError(location, "geocode_cache_size must be positive.")
        if self.geocode_disk_cache_ttl_seconds <= 0:
            raise ConfigError(location, "geocode_disk_cache_ttl_seconds must be positive.")
        if self.geocode_disk_path is not None and not str(self.geocode_disk_path).strip():
            raise ConfigError(location, "geocode_disk_path must be a non empty path when set.")
