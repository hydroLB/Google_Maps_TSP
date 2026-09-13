"""Shared enum and data types for routing workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class TravelMode(str, Enum):
    """Enumerate supported travel modes for routing."""

    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    TRANSIT = "transit"


NON_MOTORIZED_ROUTE_WARNING = (
    "Caution: Walking and bicycling routes may not include clear pedestrian or bicycle "
    "paths. Use care and follow local conditions."
)


def route_safety_warnings(mode: TravelMode) -> tuple[str, ...]:
    """Return the mandatory user-facing caution for non-motorized routes."""
    if mode in {TravelMode.WALKING, TravelMode.BICYCLING}:
        return (NON_MOTORIZED_ROUTE_WARNING,)
    return ()


class OptimizeFor(str, Enum):
    """Enumerate optimization metrics for routing."""

    TIME = "time"
    DISTANCE = "distance"


class TrafficModel(str, Enum):
    """Enumerate supported traffic models for Google Distance Matrix time estimates."""

    BEST_GUESS = "best_guess"
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"


class RouteKind(str, Enum):
    """Enumerate supported route shapes for optimization."""

    PATH = "path"
    ROUND_TRIP = "round_trip"


@dataclass(frozen=True)
class RouteResult:
    """Represent a computed route ordering and metric summary."""

    order: list[int]
    total: float
    units: str
    legs: list[float]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedAddress:
    """Bind the original user input to its normalized representation."""

    original: str
    normalized: str


@dataclass(frozen=True)
class RouteRequest:
    """Represent a routing request with validated inputs."""

    addresses: Sequence[str]
    originals: Sequence[str]
    mode: TravelMode
    optimize_for: OptimizeFor
    has_start: bool
    has_end: bool
    route_kind: RouteKind
