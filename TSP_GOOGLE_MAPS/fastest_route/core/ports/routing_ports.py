"""Core-owned contracts for route-matrix and route-cache dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import OptimizeFor, TravelMode


@runtime_checkable
class RouteMatrixPort(Protocol):
    """Define the matrix-provider behavior required by ``RoutingService``."""

    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        optimize_for: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]:
        """Build a square distance or duration matrix for route solving.

        Provides a minimal, explicit dependency contract for routing orchestration."""

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        """Build a cache key fragment representing provider-side routing factors.

        Keeps cache key semantics with the provider while decoupling core from provider types."""


@runtime_checkable
class RouteCachePort(Protocol):
    """Define the route-cache behavior required by ``RoutingService``."""

    def get_cached_route(
        self,
        addresses: Sequence[str],
        mode: str,
        metric: str,
        has_start: bool,
        has_end: bool,
        route_kind: str,
        traffic_key: str,
    ) -> tuple[list[int], float, list[float]] | None:
        """Fetch a cached route result if available.

        Allows core routing to use caching without importing concrete cache implementations."""

    def cache_route(
        self,
        addresses: Sequence[str],
        mode: str,
        metric: str,
        has_start: bool,
        has_end: bool,
        route_kind: str,
        traffic_key: str,
        order: list[int],
        total: float,
        legs: list[float],
    ) -> None:
        """Store a computed route result in cache.

        Keeps cache write behavior abstracted behind a core-defined contract."""
