from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.core.ports import RouteCachePort, RouteMatrixPort
from fastest_route.infrastructure.adapters.routing_ports import (
    CacheStoreRouteCacheAdapter,
    GoogleMapsRouteMatrixAdapter,
    build_routing_ports,
)
from fastest_route.infrastructure.cache.store import CacheStore
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.types import OptimizeFor, TravelMode

if TYPE_CHECKING:
    from collections.abc import Sequence


class _StubMatrixClient:
    def __init__(self) -> None:
        self.calls: list[tuple[Sequence[str], TravelMode, OptimizeFor, float]] = []

    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]:
        _ = cancellation_token
        self.calls.append((tuple(addresses), mode, metric, max_seconds))
        return [[0.0, 1.0], [1.0, 0.0]]

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        return f"{mode.value}:{metric.value}"


def test_google_maps_route_matrix_adapter_matches_port_contract() -> None:
    stub = _StubMatrixClient()
    adapter = GoogleMapsRouteMatrixAdapter(client=stub)

    matrix = adapter.build_matrix(
        ["A", "B"],
        TravelMode.DRIVING,
        OptimizeFor.TIME,
        cancellation_token=CancellationToken(),
        max_seconds=2.0,
    )

    assert isinstance(adapter, RouteMatrixPort)
    assert matrix == [[0.0, 1.0], [1.0, 0.0]]
    assert stub.calls == [(("A", "B"), TravelMode.DRIVING, OptimizeFor.TIME, 2.0)]
    assert (
        adapter.get_route_cache_key(mode=TravelMode.DRIVING, metric=OptimizeFor.TIME)
        == "driving:time"
    )


def test_cache_store_route_cache_adapter_matches_port_contract() -> None:
    cache_store = CacheStore(route_cache_size=10)
    adapter = CacheStoreRouteCacheAdapter(cache_store=cache_store)

    adapter.cache_route(
        ["A", "B"],
        "driving",
        "time",
        False,
        False,
        "path",
        "none",
        [0, 1],
        1.0,
        [1.0],
    )
    cached = adapter.get_cached_route(["A", "B"], "driving", "time", False, False, "path", "none")

    assert isinstance(adapter, RouteCachePort)
    assert cached == ([0, 1], 1.0, [1.0])


def test_build_routing_ports_returns_protocol_instances() -> None:
    matrix_port, cache_port = build_routing_ports(
        maps_client=_StubMatrixClient(),
        cache_store=CacheStore(route_cache_size=10),
    )

    assert isinstance(matrix_port, RouteMatrixPort)
    assert isinstance(cache_port, RouteCachePort)
