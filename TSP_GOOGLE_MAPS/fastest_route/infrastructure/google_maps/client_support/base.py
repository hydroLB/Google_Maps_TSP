"""Typed host contract for GoogleMapsClient mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    import requests

    from fastest_route.config.registry import AppConfig
    from fastest_route.infrastructure.cache.distance_cache import DistanceCache
    from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache
    from fastest_route.infrastructure.google_maps.http_client import GoogleMapsHttpClient
    from fastest_route.infrastructure.rate_limit import RateLimiter
    from fastest_route.infrastructure.retry import RetryPolicy
    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import OptimizeFor, TravelMode


class GoogleMapsClientHost:
    """Describe the attributes expected by GoogleMapsClient mixins."""

    _config: AppConfig
    _cache: DistanceCache
    _geocode_cache: GeocodeCache
    _rate_limiter: RateLimiter
    _retry_policy: RetryPolicy
    _session: requests.Session
    _http: GoogleMapsHttpClient
    _api_key_override: str | None

    def _api_key(self, location: str) -> str:
        raise NotImplementedError

    def _request_json(
        self,
        url: str,
        params: Mapping[str, str],
        *,
        cancellation_token: CancellationToken | None = None,
        deadline: float | None = None,
    ) -> Mapping[str, object]:
        raise NotImplementedError

    def _traffic_departure_time(self, *, mode: TravelMode, metric: OptimizeFor) -> str | None:
        raise NotImplementedError

    def _traffic_cache_departure_time(self, *, mode: TravelMode, metric: OptimizeFor) -> str | None:
        """Declare the bounded departure-time variant used for cache keys."""

        raise NotImplementedError

    def _traffic_model(self, *, mode: TravelMode, metric: OptimizeFor) -> str | None:
        raise NotImplementedError

    def _distance_matrix_params(
        self, *, base: Mapping[str, str], mode: TravelMode, metric: OptimizeFor
    ) -> dict[str, str]:
        raise NotImplementedError

    def _use_duration_in_traffic(self, *, mode: TravelMode, metric: OptimizeFor) -> bool:
        raise NotImplementedError

    def _redact_address(self, address: str) -> str:
        raise NotImplementedError

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        raise NotImplementedError
