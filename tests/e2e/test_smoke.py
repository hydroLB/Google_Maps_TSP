from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

from fastest_route.core.routing.routing_service import RoutingService
from fastest_route.infrastructure.cache.distance_cache import DistanceCache
from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache
from fastest_route.infrastructure.cache.store import CacheStore
from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
from fastest_route.infrastructure.rate_limit import RateLimiter
from fastest_route.infrastructure.retry import RetryPolicy
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.types import OptimizeFor, RouteKind, RouteRequest, TravelMode

if TYPE_CHECKING:
    from pathlib import Path

    from fastest_route.config.registry import AppConfig


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self.text = json.dumps(payload)


def _build_client(config: AppConfig, cache_path: Path) -> GoogleMapsClient:
    cache = DistanceCache(cache_path, ttl_seconds=config.cache.disk_cache_ttl_seconds)
    geocode_cache = GeocodeCache(
        memory_max_items=config.cache.geocode_cache_size,
        disk_path=None,
        disk_ttl_seconds=config.cache.geocode_disk_cache_ttl_seconds,
    )
    rate_limiter = RateLimiter(
        config.rate_limit.requests_per_second,
        config.rate_limit.burst,
        config.rate_limit.max_wait_seconds,
    )
    retry_policy = RetryPolicy(
        max_attempts=config.http.retry_max_attempts,
        base_delay_seconds=config.http.retry_base_delay_seconds,
        max_delay_seconds=config.http.retry_max_delay_seconds,
        jitter_ratio=config.http.retry_jitter_ratio,
        retry_statuses=config.http.retry_statuses,
    )
    return GoogleMapsClient(
        config=config,
        cache=cache,
        geocode_cache=geocode_cache,
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
    )


def test_end_to_end_route_smoke(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    cache_store = CacheStore(route_cache_size=app_config.cache.route_cache_size)
    service = RoutingService(config=app_config, maps_client=client, cache_store=cache_store)

    distances = {
        ("A", "B"): (300, 5000),
        ("A", "C"): (540, 9000),
        ("B", "A"): (300, 5000),
        ("B", "C"): (60, 1000),
        ("C", "A"): (540, 9000),
        ("C", "B"): (60, 1000),
    }

    def fake_get(_url: str, *, params: dict[str, str], timeout: float) -> FakeResponse:
        origins = params["origins"].split("|")
        destinations = params["destinations"].split("|")
        payload = {
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        {
                            "status": "OK",
                            "duration": {
                                "value": 0
                                if origin == destination
                                else distances[(origin, destination)][0]
                            },
                            "distance": {
                                "value": 0
                                if origin == destination
                                else distances[(origin, destination)][1]
                            },
                        }
                        for destination in destinations
                    ]
                }
                for origin in origins
            ],
        }
        return FakeResponse(200, payload)

    mock_session = Mock()
    mock_session.get = Mock(side_effect=fake_get)
    client._session = mock_session

    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = service.compute_route(request, cancellation_token=CancellationToken())
    assert result.total == 6.0
    assert result.units == "min"
    assert set(result.order) == {0, 1, 2}
    assert mock_session.get.call_count == 1
