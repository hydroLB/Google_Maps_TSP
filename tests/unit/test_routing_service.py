from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastest_route.core.routing.routing_service import RoutingService
from fastest_route.infrastructure.cache.store import CacheStore
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import ExternalServiceError, ValidationError
from fastest_route.shared.types import (
    NON_MOTORIZED_ROUTE_WARNING,
    OptimizeFor,
    RouteKind,
    RouteRequest,
    TravelMode,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.config.registry import AppConfig


class StubMapsClient:
    def __init__(self, matrix: Sequence[Sequence[float]]) -> None:
        self._matrix = matrix
        self.calls = 0

    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]:
        self.calls += 1
        return [list(row) for row in self._matrix]

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        _ = mode
        _ = metric
        return "none"


def test_routing_service_caches_results(app_config: AppConfig) -> None:
    matrix = [
        [0.0, 5.0, 9.0],
        [5.0, 0.0, 1.0],
        [9.0, 1.0, 0.0],
    ]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(
        route_cache_size=10,
    )
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )

    first = service.compute_route(request, cancellation_token=CancellationToken())
    second = service.compute_route(request, cancellation_token=CancellationToken())

    assert first.total == 6.0
    assert second.total == 6.0
    assert maps_client.calls == 1


@pytest.mark.parametrize("mode", [TravelMode.WALKING, TravelMode.BICYCLING])
def test_routing_service_attaches_non_motorized_warning_on_fresh_and_cached_results(
    app_config: AppConfig, mode: TravelMode
) -> None:
    """Walking and bicycling results retain their safety caution across route-cache hits."""
    maps_client = StubMapsClient(
        [
            [0.0, 5.0, 9.0],
            [5.0, 0.0, 1.0],
            [9.0, 1.0, 0.0],
        ]
    )
    cache_store = CacheStore(
        route_cache_size=10,
    )
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=mode,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )

    fresh = service.compute_route(request, cancellation_token=CancellationToken())
    cached = service.compute_route(request, cancellation_token=CancellationToken())

    assert fresh.warnings == (NON_MOTORIZED_ROUTE_WARNING,)
    assert cached.warnings == (NON_MOTORIZED_ROUTE_WARNING,)
    assert maps_client.calls == 1


def test_routing_service_fixed_start(app_config: AppConfig) -> None:
    matrix = [
        [0.0, 5.0, 9.0, 8.0],
        [5.0, 0.0, 1.0, 4.0],
        [9.0, 1.0, 0.0, 2.0],
        [8.0, 4.0, 2.0, 0.0],
    ]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(
        route_cache_size=10,
    )
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=["Start", "A", "B", "C"],
        originals=["Start", "A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=True,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = service.compute_route(request, cancellation_token=CancellationToken())
    assert result.order[0] == 0
    assert result.units == "min"


def test_routing_service_fixed_end(app_config: AppConfig) -> None:
    matrix = [
        [0.0, 1.0, 10.0, 10.0],
        [1.0, 0.0, 1.0, 10.0],
        [10.0, 1.0, 0.0, 1.0],
        [10.0, 10.0, 1.0, 0.0],
    ]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(
        route_cache_size=10,
    )
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=["A", "B", "C", "End"],
        originals=["A", "B", "C", "End"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=True,
        route_kind=RouteKind.PATH,
    )
    result = service.compute_route(request, cancellation_token=CancellationToken())
    assert result.order[-1] == 3
    assert result.total == 3.0


def test_routing_service_round_trip_includes_return_leg(app_config: AppConfig) -> None:
    matrix = [
        [0.0, 1.0, 5.0],
        [1.0, 0.0, 1.0],
        [5.0, 1.0, 0.0],
    ]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(
        route_cache_size=10,
    )
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.ROUND_TRIP,
    )
    result = service.compute_route(request, cancellation_token=CancellationToken())
    # Best cycle is 0 -> 1 -> 2 -> 0 with cost 1 + 1 + 5.
    assert result.total == 7.0


def test_routing_service_rejects_empty_addresses(app_config: AppConfig) -> None:
    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=[],
        originals=[],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    with pytest.raises(ValidationError):
        service.compute_route(request, cancellation_token=CancellationToken())


def test_routing_service_requires_min_stops(app_config: AppConfig) -> None:
    matrix = [[0.0, 1.0], [1.0, 0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    request = RouteRequest(
        addresses=["A", "B"],
        originals=["A", "B"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    with pytest.raises(ValidationError):
        service.compute_route(request, cancellation_token=CancellationToken())


@pytest.mark.parametrize(
    ("addresses", "originals", "has_start", "has_end", "route_kind", "message"),
    [
        (
            ["Start", "A", "B", "End"],
            ["Start", "A", "B", "End"],
            True,
            True,
            RouteKind.PATH,
            "Not enough stops",
        ),
        (
            ["Start", "A", "B", "C", "D", "E", "F", "G", "H"],
            ["Start", "A", "B", "C", "D", "E", "F", "G", "H"],
            True,
            False,
            RouteKind.PATH,
            "Too many stops",
        ),
        (
            ["A", "B", "C"],
            ["A", "B"],
            False,
            False,
            RouteKind.PATH,
            "counts must match",
        ),
        (
            ["Only endpoint"],
            ["Only endpoint"],
            True,
            True,
            RouteKind.PATH,
            "Endpoint flags are incompatible",
        ),
        (
            ["A", "B", "C", "End"],
            ["A", "B", "C", "End"],
            False,
            True,
            RouteKind.ROUND_TRIP,
            "Round trips do not support a fixed end",
        ),
    ],
)
def test_routing_service_rejects_invalid_request_shape_before_dependencies(
    app_config: AppConfig,
    addresses: list[str],
    originals: list[str],
    has_start: bool,
    has_end: bool,
    route_kind: RouteKind,
    message: str,
) -> None:
    """Core request invariants are enforced before cache or matrix-provider access."""
    maps_client = StubMapsClient([[0.0]])

    class FailingCacheStore:
        def get_cached_route(self, *_args: object) -> None:
            raise AssertionError("cache lookup must not run for an invalid request")

        def cache_route(self, *_args: object) -> None:
            raise AssertionError("cache write must not run for an invalid request")

    service = RoutingService(
        config=app_config,
        maps_client=maps_client,
        cache_store=FailingCacheStore(),
    )
    request = RouteRequest(
        addresses=addresses,
        originals=originals,
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=has_start,
        has_end=has_end,
        route_kind=route_kind,
    )

    with pytest.raises(ValidationError, match=message):
        service.compute_route(request, cancellation_token=CancellationToken())

    assert maps_client.calls == 0


def test_solve_with_fixed_start_requires_two_nodes(app_config: AppConfig) -> None:
    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    with pytest.raises(ValidationError):
        service._solve_with_fixed_start(matrix)


def test_routing_service_requires_config() -> None:
    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    with pytest.raises(ValidationError):
        RoutingService(config=None, maps_client=maps_client, cache_store=cache_store)


def test_routing_service_invalid_config_type() -> None:
    class BadConfig:
        pass

    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    with pytest.raises(ValidationError):
        RoutingService(config=BadConfig(), maps_client=maps_client, cache_store=cache_store)


def test_routing_service_wraps_external_errors(app_config: AppConfig) -> None:
    class ErrorMapsClient:
        def build_matrix(
            self,
            addresses: Sequence[str],
            mode: TravelMode,
            metric: OptimizeFor,
            *,
            cancellation_token: CancellationToken,
            max_seconds: float,
        ) -> list[list[float]]:
            raise ExternalServiceError("test", "boom")

        def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
            _ = mode
            _ = metric
            return "none"

    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(
        config=app_config, maps_client=ErrorMapsClient(), cache_store=cache_store
    )
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    with pytest.raises(ExternalServiceError):
        service.compute_route(request, cancellation_token=CancellationToken())


def test_routing_service_wraps_attribute_errors(app_config: AppConfig) -> None:
    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)

    class BadRequest:
        pass

    with pytest.raises(ValidationError):
        service.compute_route(BadRequest(), cancellation_token=CancellationToken())


def test_solve_with_fixed_start_wraps_type_errors(app_config: AppConfig) -> None:
    matrix = [1, 2]
    maps_client = StubMapsClient([[0.0, 1.0], [1.0, 0.0]])
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    with pytest.raises(ValidationError):
        service._solve_with_fixed_start(matrix)


def test_solve_with_fixed_start_wraps_external_errors(app_config: AppConfig) -> None:
    matrix = [[0.0, 1.0], [1.0, 0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    service._solver.solve = lambda _mtx: (_ for _ in ()).throw(ExternalServiceError("test", "boom"))
    with pytest.raises(ExternalServiceError):
        service._solve_with_fixed_start(matrix)


def test_units_distance(app_config: AppConfig) -> None:
    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    assert service._units(OptimizeFor.DISTANCE) == "km"


def test_units_invalid_type(app_config: AppConfig) -> None:
    matrix = [[0.0]]
    maps_client = StubMapsClient(matrix)
    cache_store = CacheStore(route_cache_size=10)
    service = RoutingService(config=app_config, maps_client=maps_client, cache_store=cache_store)
    with pytest.raises(ValidationError):
        service._units("bad")
