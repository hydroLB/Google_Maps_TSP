"""GoogleMapsClient helpers for traffic-aware request policy and cache key variants."""

from __future__ import annotations

import time
from collections.abc import Mapping

from fastest_route.infrastructure.google_maps.client_support.base import GoogleMapsClientHost
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import OptimizeFor, TrafficModel, TravelMode

_LIVE_TRAFFIC_CACHE_BUCKET_SECONDS = 300


class GoogleMapsClientTrafficMixin(GoogleMapsClientHost):
    """Provide GoogleMapsClient methods for traffic-aware request decisions."""

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        """Return a traffic-sensitive route-cache variant.

        Departure time and traffic model affect Google's duration estimates, so both must
        participate in the cache key."""
        location = "fastest_route.infrastructure.google_maps.client_support.traffic.GoogleMapsClientTrafficMixin.get_route_cache_key"
        if not isinstance(mode, TravelMode):
            raise ValidationError(location, "mode must be a TravelMode.")
        if not isinstance(metric, OptimizeFor):
            raise ValidationError(location, "metric must be an OptimizeFor.")
        departure_time = self._traffic_cache_departure_time(mode=mode, metric=metric)
        traffic_model = self._traffic_model(mode=mode, metric=metric)
        if departure_time is None and traffic_model is None:
            return "none"
        return f"traffic={departure_time or ''}|{traffic_model or ''}"

    def _traffic_cache_departure_time(self, *, mode: TravelMode, metric: OptimizeFor) -> str | None:
        """Return a bounded cache variant for traffic-sensitive departure times.

        Google interprets ``departure_time=now`` at request time. Keying that value literally
        would allow a route calculated hours earlier to remain cached for the process lifetime.
        Five-minute buckets retain useful deduplication while bounding traffic staleness.
        Explicit Unix departure times remain stable and are safe to cache directly.
        """

        departure_time = self._traffic_departure_time(mode=mode, metric=metric)
        if departure_time is None or departure_time.lower() != "now":
            return departure_time
        bucket = int(time.time() // _LIVE_TRAFFIC_CACHE_BUCKET_SECONDS)
        return f"now@{bucket}"

    def _use_duration_in_traffic(self, *, mode: TravelMode, metric: OptimizeFor) -> bool:
        """Return whether this request should use Google's traffic-aware duration."""
        try:
            if metric != OptimizeFor.TIME:
                return False
            if mode.value != "driving":
                return False
            return bool(self._config.google_maps.traffic_aware_time)
        except AttributeError:
            return False

    def _traffic_departure_time(self, *, mode: TravelMode, metric: OptimizeFor) -> str | None:
        """Resolve the departure time for a traffic-aware driving request."""
        if not self._use_duration_in_traffic(mode=mode, metric=metric):
            return None
        try:
            return self._config.google_maps.departure_time.strip()
        except AttributeError:
            return None

    def _traffic_model(self, *, mode: TravelMode, metric: OptimizeFor) -> str | None:
        """Resolve Google's estimation model for a traffic-aware request."""
        if not self._use_duration_in_traffic(mode=mode, metric=metric):
            return None
        try:
            model = self._config.google_maps.traffic_model
            if isinstance(model, TrafficModel):
                return model.value
            return str(model)
        except AttributeError:
            return None

    def _distance_matrix_params(
        self,
        *,
        base: Mapping[str, str],
        mode: TravelMode,
        metric: OptimizeFor,
    ) -> dict[str, str]:
        """Add applicable traffic settings to distance-matrix parameters."""
        location = "fastest_route.infrastructure.google_maps.client_support.traffic.GoogleMapsClientTrafficMixin._distance_matrix_params"
        if not isinstance(base, Mapping):
            raise ValidationError(location, "base params must be a mapping.")
        params: dict[str, str] = dict(base)
        if self._use_duration_in_traffic(mode=mode, metric=metric):
            departure_time = self._traffic_departure_time(mode=mode, metric=metric)
            traffic_model = self._traffic_model(mode=mode, metric=metric)
            if departure_time is None or traffic_model is None:
                raise ValidationError(
                    location, "Traffic-aware settings are enabled but incomplete."
                )
            params["departure_time"] = departure_time
            params["traffic_model"] = traffic_model
        return params
