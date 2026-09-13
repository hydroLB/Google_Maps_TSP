"""In-memory cache store for computed route results.

Centralizes cache ownership and sizing in one place."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.infrastructure.cache.lru_cache import LruCache
from fastest_route.shared.errors import CacheError

if TYPE_CHECKING:
    from collections.abc import Sequence


class CacheStore:
    """Hold the in-memory cache for computed routes.

    Centralizes route-cache ownership and sizing."""

    def __init__(
        self,
        *,
        route_cache_size: int,
    ) -> None:
        """Initialize the route cache.

        Keeps cache sizing explicit and validated."""
        location = "fastest_route.infrastructure.cache.store.CacheStore.__init__"
        try:
            if route_cache_size <= 0:
                raise CacheError(location, "route_cache_size must be positive.")
            self.route_cache: LruCache[
                tuple[tuple[str, ...], str, str, bool, bool, str, str],
                tuple[list[int], float, list[float]],
            ] = LruCache(route_cache_size)
        except CacheError as exc:
            raise CacheError(location, str(exc)) from exc

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
        """Store a route computation result in cache.

        Avoids recomputing identical routes."""
        location = "fastest_route.infrastructure.cache.store.CacheStore.cache_route"
        try:
            if not addresses:
                raise CacheError(location, "addresses must not be empty.")
            if not legs:
                raise CacheError(location, "legs must not be empty.")
            if not isinstance(traffic_key, str) or not traffic_key.strip():
                raise CacheError(location, "traffic_key must be a non empty string.")
            key = (tuple(addresses), mode, metric, has_start, has_end, route_kind, traffic_key)
            self.route_cache.set(key, (list(order), total, list(legs)))
        except CacheError as exc:
            raise CacheError(location, str(exc)) from exc

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
        """Retrieve a cached route computation if available.

        Reduces redundant routing computation."""
        location = "fastest_route.infrastructure.cache.store.CacheStore.get_cached_route"
        try:
            if not addresses:
                raise CacheError(location, "addresses must not be empty.")
            if not isinstance(traffic_key, str) or not traffic_key.strip():
                raise CacheError(location, "traffic_key must be a non empty string.")
            key = (tuple(addresses), mode, metric, has_start, has_end, route_kind, traffic_key)
            cached = self.route_cache.get(key)
            if cached is None:
                return None
            order, total, legs = cached
            return list(order), total, list(legs)
        except CacheError as exc:
            raise CacheError(location, str(exc)) from exc
