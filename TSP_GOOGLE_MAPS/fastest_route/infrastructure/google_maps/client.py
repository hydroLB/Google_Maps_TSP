"""Google Maps API client with caching, retries, and rate limiting."""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING

import requests

from fastest_route.infrastructure.google_maps.client_support import (
    GoogleMapsClientMatrixMixin,
    GoogleMapsClientRequestMixin,
    GoogleMapsClientTrafficMixin,
)
from fastest_route.infrastructure.google_maps.http_client import GoogleMapsHttpClient
from fastest_route.shared.errors import ValidationError

__all__ = ["GoogleMapsClient", "hashlib", "time"]

if TYPE_CHECKING:
    from fastest_route.config.registry import AppConfig
    from fastest_route.infrastructure.cache.distance_cache import DistanceCache
    from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache
    from fastest_route.infrastructure.rate_limit import RateLimiter
    from fastest_route.infrastructure.retry import RetryPolicy


class GoogleMapsClient(
    GoogleMapsClientRequestMixin,
    GoogleMapsClientTrafficMixin,
    GoogleMapsClientMatrixMixin,
):
    """Provide Google Maps API access with caching, retries, and rate limiting."""

    def __init__(
        self,
        *,
        config: AppConfig,
        cache: DistanceCache,
        geocode_cache: GeocodeCache,
        rate_limiter: RateLimiter,
        retry_policy: RetryPolicy,
    ) -> None:
        location = "fastest_route.infrastructure.google_maps.client.GoogleMapsClient.__init__"
        try:
            _validate_google_maps_client_dependencies(
                location=location,
                config=config,
                geocode_cache=geocode_cache,
            )
            self._config = config
            self._cache = cache
            self._geocode_cache = geocode_cache
            self._rate_limiter = rate_limiter
            self._retry_policy = retry_policy
            self._session = requests.Session()
            self._http = GoogleMapsHttpClient(
                session_provider=lambda: self._session,
                timeout_seconds=self._config.http.timeout_seconds,
                rate_limiter=self._rate_limiter,
                retry_policy=self._retry_policy,
                retry_statuses=self._retry_policy.retry_statuses,
            )
            self._api_key_override: str | None = None
        except ValidationError:
            raise
        except AttributeError as exc:
            raise ValidationError(location, "GoogleMapsClient dependencies are invalid.") from exc

    def has_api_key(self) -> bool:
        """Return whether distance and geocoding requests have a configured API key."""
        try:
            key = self._api_key_override or self._config.google_maps.api_key
            return bool(isinstance(key, str) and key.strip())
        except AttributeError:
            return False

    def set_api_key(self, api_key: str) -> None:
        """Set an in-memory API key so interactive setup does not require a restart."""
        location = "fastest_route.infrastructure.google_maps.client.GoogleMapsClient.set_api_key"
        if not isinstance(api_key, str):
            raise ValidationError(location, "api_key must be a string.")
        if not api_key.strip():
            raise ValidationError(location, "api_key must not be empty.")
        self._api_key_override = api_key.strip()


def _validate_google_maps_client_dependencies(
    *,
    location: str,
    config: object,
    geocode_cache: object,
) -> None:
    """Validate dependencies before allocating the HTTP client."""
    if not getattr(config, "google_maps", None):
        raise ValidationError(location, "Google Maps config is required.")
    if not geocode_cache:
        raise ValidationError(location, "geocode_cache is required.")
