"""Parsers for config values that map to application enums."""

from __future__ import annotations

from fastest_route.shared.errors import ConfigError
from fastest_route.shared.types import OptimizeFor, TrafficModel, TravelMode


def parse_travel_mode(value: object, location: str) -> TravelMode:
    """Parse and validate a travel mode string into a TravelMode enum."""
    if not isinstance(value, str):
        raise ConfigError(location, "Travel mode must be a string.")
    normalized = value.strip().lower()
    try:
        return TravelMode(normalized)
    except ValueError as exc:
        raise ConfigError(location, f"Invalid travel mode '{value}'.") from exc


def parse_optimize_for(value: object, location: str) -> OptimizeFor:
    """Parse and validate an optimization metric string into an OptimizeFor enum."""
    if not isinstance(value, str):
        raise ConfigError(location, "Optimize_for must be a string.")
    normalized = value.strip().lower()
    try:
        return OptimizeFor(normalized)
    except ValueError as exc:
        raise ConfigError(location, f"Invalid optimize_for value '{value}'.") from exc


def parse_traffic_model(value: object, location: str) -> TrafficModel:
    """Parse and validate a traffic model string into a TrafficModel enum."""
    if not isinstance(value, str):
        raise ConfigError(location, "traffic_model must be a string.")
    normalized = value.strip().lower()
    try:
        return TrafficModel(normalized)
    except ValueError as exc:
        raise ConfigError(location, f"Invalid traffic_model value '{value}'.") from exc
