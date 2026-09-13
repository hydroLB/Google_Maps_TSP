"""Routing configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_float, get_int, get_str
from fastest_route.config.loading.parsers import (
    parse_optimize_for,
    parse_travel_mode,
)
from fastest_route.config.registry import RoutingConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_routing_config(*, routing_section: Mapping[str, object], location: str) -> RoutingConfig:
    """Build a RoutingConfig from the TOML routing section."""
    return RoutingConfig(
        max_exact=get_int(routing_section, "max_exact", 7, location),
        two_opt_max_passes=get_int(routing_section, "two_opt_max_passes", 8, location),
        nearest_neighbor_start_index=get_int(
            routing_section, "nearest_neighbor_start_index", 0, location
        ),
        default_mode=parse_travel_mode(
            get_str(routing_section, "default_mode", "driving", location), location
        ),
        default_optimize_for=parse_optimize_for(
            get_str(routing_section, "default_optimize_for", "time", location), location
        ),
        max_compute_seconds=get_float(routing_section, "max_compute_seconds", 60.0, location),
    )
