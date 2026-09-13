"""Adapter boundary mapping infrastructure implementations to core routing ports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import OptimizeFor, TravelMode


class _MatrixClientDependency(Protocol):
    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]: ...

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str: ...


class _RouteCacheDependency(Protocol):
    def get_cached_route(
        self,
        addresses: Sequence[str],
        mode: str,
        metric: str,
        has_start: bool,
        has_end: bool,
        route_kind: str,
        traffic_key: str,
    ) -> tuple[list[int], float, list[float]] | None: ...

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
    ) -> None: ...


def _require_callable(
    *,
    dependency: object,
    method_name: str,
    location: str,
) -> None:
    """Fail fast when an adapted dependency does not provide a required method."""
    member = getattr(dependency, method_name, None)
    if not callable(member):
        raise ValidationError(
            location,
            f"Dependency {dependency.__class__.__name__} must define callable '{method_name}'.",
        )


class GoogleMapsRouteMatrixAdapter:
    """Adapter that exposes GoogleMapsClient through RouteMatrixPort."""

    def __init__(self, *, client: _MatrixClientDependency) -> None:
        location = "fastest_route.infrastructure.adapters.routing_ports.GoogleMapsRouteMatrixAdapter.__init__"
        if client is None:
            raise ValidationError(location, "client is required.")
        _require_callable(dependency=client, method_name="build_matrix", location=location)
        _require_callable(dependency=client, method_name="get_route_cache_key", location=location)
        self._client = client

    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        optimize_for: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]:
        """Delegate matrix construction to the underlying provider."""
        return self._client.build_matrix(
            addresses,
            mode,
            optimize_for,
            cancellation_token=cancellation_token,
            max_seconds=max_seconds,
        )

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        """Keep provider-specific traffic key logic behind the routing boundary."""
        return self._client.get_route_cache_key(mode=mode, metric=metric)


class CacheStoreRouteCacheAdapter:
    """Adapter that exposes CacheStore through RouteCachePort."""

    def __init__(self, *, cache_store: _RouteCacheDependency) -> None:
        location = "fastest_route.infrastructure.adapters.routing_ports.CacheStoreRouteCacheAdapter.__init__"
        if cache_store is None:
            raise ValidationError(location, "cache_store is required.")
        _require_callable(dependency=cache_store, method_name="get_cached_route", location=location)
        _require_callable(dependency=cache_store, method_name="cache_route", location=location)
        self._cache_store = cache_store

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
        """Delegate route cache lookups to the underlying cache store."""
        return self._cache_store.get_cached_route(
            addresses,
            mode,
            metric,
            has_start,
            has_end,
            route_kind,
            traffic_key,
        )

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
        """Delegate route cache writes to the underlying cache store."""
        self._cache_store.cache_route(
            addresses,
            mode,
            metric,
            has_start,
            has_end,
            route_kind,
            traffic_key,
            order,
            total,
            legs,
        )


def build_routing_ports(
    *,
    maps_client: _MatrixClientDependency,
    cache_store: _RouteCacheDependency,
) -> tuple[GoogleMapsRouteMatrixAdapter, CacheStoreRouteCacheAdapter]:
    """Construct route matrix and cache adapters for RoutingService wiring."""
    location = "fastest_route.infrastructure.adapters.routing_ports.build_routing_ports"
    if maps_client is None:
        raise ValidationError(location, "maps_client is required.")
    if cache_store is None:
        raise ValidationError(location, "cache_store is required.")

    matrix_port = GoogleMapsRouteMatrixAdapter(client=maps_client)
    cache_port = CacheStoreRouteCacheAdapter(cache_store=cache_store)
    return matrix_port, cache_port


__all__ = [
    "CacheStoreRouteCacheAdapter",
    "GoogleMapsRouteMatrixAdapter",
    "build_routing_ports",
]
