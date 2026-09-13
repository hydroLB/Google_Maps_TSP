"""Routing configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ConfigError

if TYPE_CHECKING:
    from fastest_route.shared.types import OptimizeFor, TravelMode


@dataclass(frozen=True)
class RoutingConfig:
    """Hold routing algorithm and tuning parameters."""

    max_exact: int
    two_opt_max_passes: int
    nearest_neighbor_start_index: int
    default_mode: TravelMode
    default_optimize_for: OptimizeFor
    max_compute_seconds: float

    def validate(self) -> None:
        """Validate routing configuration values."""
        location = "fastest_route.config.registry.RoutingConfig.validate"
        if self.max_exact <= 1:
            raise ConfigError(location, "max_exact must be greater than 1.")
        if self.two_opt_max_passes <= 0:
            raise ConfigError(location, "two_opt_max_passes must be positive.")
        if self.nearest_neighbor_start_index < 0:
            raise ConfigError(location, "nearest_neighbor_start_index must be zero or greater.")
        if self.max_compute_seconds <= 0:
            raise ConfigError(location, "max_compute_seconds must be positive.")
