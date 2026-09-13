"""GoogleMapsClient helpers for distance lookups, logging, and matrix construction.

Separates heavier routing-related API logic from lightweight request helpers and traffic policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.infrastructure.cache.keys import build_distance_key
from fastest_route.infrastructure.google_maps import client as client_module
from fastest_route.infrastructure.google_maps.client_support.base import GoogleMapsClientHost
from fastest_route.infrastructure.google_maps.parsing import (
    parse_distance_matrix_value,
    parse_distance_matrix_values,
)
from fastest_route.observability.logger import get_logger
from fastest_route.shared.errors import (
    DeadlineExceededError,
    ExternalServiceError,
    ValidationError,
    error_code_for_exception,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import OptimizeFor, TravelMode

logger = get_logger(__name__, component="google_maps")

_MAX_LEGACY_MATRIX_ELEMENTS = 100


class GoogleMapsClientMatrixMixin(GoogleMapsClientHost):
    """Provide GoogleMapsClient methods for single distance lookups and full matrix construction.

    Groups heavier routing-related API logic into a focused implementation module."""

    def get_distance(
        self,
        origin: str,
        destination: str,
        mode: TravelMode,
        metric: OptimizeFor,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> float:
        """Retrieve a distance or duration between two points.

        Centralizes caching and response parsing so routing code stays deterministic and small."""
        location = "fastest_route.infrastructure.google_maps.client_support.matrix.GoogleMapsClientMatrixMixin.get_distance"
        self._validate_distance_inputs(
            location=location,
            origin=origin,
            destination=destination,
            cancellation_token=cancellation_token,
        )
        departure_time = self._traffic_departure_time(mode=mode, metric=metric)
        cache_departure_time = self._traffic_cache_departure_time(mode=mode, metric=metric)
        traffic_model = self._traffic_model(mode=mode, metric=metric)
        cache_key = build_distance_key(
            origin,
            destination,
            mode.value,
            metric.value,
            departure_time=cache_departure_time,
            traffic_model=traffic_model,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            return self._retry_policy.execute(
                lambda: self._perform_distance_lookup(
                    origin=origin,
                    destination=destination,
                    mode=mode,
                    metric=metric,
                    cache_key=cache_key,
                    cancellation_token=cancellation_token,
                    location=location,
                ),
                location=location,
                cancellation_token=cancellation_token,
            )
        except ExternalServiceError as exc:
            self._log_distance_lookup_failure(
                exc=exc,
                origin=origin,
                destination=destination,
                mode=mode,
                metric=metric,
                departure_time=departure_time,
                traffic_model=traffic_model,
            )
            raise ExternalServiceError(location, "Distance lookup failed.") from exc

    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]:
        """Build a full distance matrix for a set of addresses.

        Ensures matrix construction is time-bounded and cancellation-aware for responsive UI behavior."""
        location = "fastest_route.infrastructure.google_maps.client_support.matrix.GoogleMapsClientMatrixMixin.build_matrix"
        self._validate_matrix_inputs(
            location=location,
            addresses=addresses,
            cancellation_token=cancellation_token,
            max_seconds=max_seconds,
        )
        deadline = client_module.time.monotonic() + max_seconds
        try:
            cancellation_token.raise_if_cancelled(location)
            self._enforce_matrix_deadline(
                deadline=deadline,
                cancellation_token=cancellation_token,
                location=location,
            )
            cached = self._read_cached_matrix(addresses=addresses, mode=mode, metric=metric)
            if cached is not None:
                self._enforce_matrix_deadline(
                    deadline=deadline,
                    cancellation_token=cancellation_token,
                    location=location,
                )
                return cached
            self._enforce_matrix_deadline(
                deadline=deadline,
                cancellation_token=cancellation_token,
                location=location,
            )
            matrix = self._retry_policy.execute(
                lambda: self._perform_matrix_lookup(
                    addresses=addresses,
                    mode=mode,
                    metric=metric,
                    cancellation_token=cancellation_token,
                    location=location,
                    deadline=deadline,
                ),
                location=location,
                cancellation_token=cancellation_token,
                deadline=deadline,
            )
            self._enforce_matrix_deadline(
                deadline=deadline,
                cancellation_token=cancellation_token,
                location=location,
            )
            return matrix
        except DeadlineExceededError as exc:
            raise DeadlineExceededError(location, "Matrix build exceeded time limit.") from exc
        except ExternalServiceError:
            raise
        except ValidationError:
            raise
        except (IndexError, TypeError) as exc:
            raise ExternalServiceError(location, "Failed to build distance matrix.") from exc

    def _read_cached_matrix(
        self,
        *,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
    ) -> list[list[float]] | None:
        """Return a complete cached matrix, never a partially cached result."""

        size = len(addresses)
        matrix = [[0.0 for _ in range(size)] for _ in range(size)]
        cache_departure_time = self._traffic_cache_departure_time(mode=mode, metric=metric)
        traffic_model = self._traffic_model(mode=mode, metric=metric)
        for row_index, origin in enumerate(addresses):
            for column_index, destination in enumerate(addresses):
                if row_index == column_index:
                    continue
                key = build_distance_key(
                    origin,
                    destination,
                    mode.value,
                    metric.value,
                    departure_time=cache_departure_time,
                    traffic_model=traffic_model,
                )
                value = self._cache.get(key)
                if value is None:
                    return None
                matrix[row_index][column_index] = value
        return matrix

    def _perform_matrix_lookup(
        self,
        *,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
        cancellation_token: CancellationToken,
        location: str,
        deadline: float,
    ) -> list[list[float]]:
        """Fetch the complete route matrix in one provider request and cache each directed leg."""

        cancellation_token.raise_if_cancelled(location)
        joined_addresses = "|".join(addresses)
        data = self._request_json(
            self._config.google_maps.distance_matrix_url,
            self._distance_matrix_params(
                base={
                    "origins": joined_addresses,
                    "destinations": joined_addresses,
                    "mode": mode.value,
                    "key": self._api_key(location),
                },
                mode=mode,
                metric=metric,
            ),
            cancellation_token=cancellation_token,
            deadline=deadline,
        )
        matrix = parse_distance_matrix_values(
            data,
            metric=metric,
            expected_size=len(addresses),
            use_duration_in_traffic=self._use_duration_in_traffic(mode=mode, metric=metric),
            location=location,
        )
        self._enforce_matrix_deadline(
            deadline=deadline,
            cancellation_token=cancellation_token,
            location=location,
        )
        cache_departure_time = self._traffic_cache_departure_time(mode=mode, metric=metric)
        traffic_model = self._traffic_model(mode=mode, metric=metric)
        for row_index, origin in enumerate(addresses):
            for column_index, destination in enumerate(addresses):
                if row_index == column_index:
                    continue
                key = build_distance_key(
                    origin,
                    destination,
                    mode.value,
                    metric.value,
                    departure_time=cache_departure_time,
                    traffic_model=traffic_model,
                )
                self._cache.set(key, matrix[row_index][column_index])
        return matrix

    def _enforce_matrix_deadline(
        self,
        *,
        deadline: float,
        cancellation_token: CancellationToken,
        location: str,
    ) -> None:
        cancellation_token.raise_if_cancelled(location)
        if client_module.time.monotonic() >= deadline:
            raise DeadlineExceededError(location, "Matrix build exceeded time limit.")

    def _validate_distance_inputs(
        self,
        *,
        location: str,
        origin: str,
        destination: str,
        cancellation_token: CancellationToken | None,
    ) -> None:
        """Validate the inputs for a single distance lookup.

        Keeps get_distance focused on orchestration rather than boundary validation."""
        if cancellation_token is not None:
            cancellation_token.raise_if_cancelled(location)
        if not isinstance(origin, str) or not isinstance(destination, str):
            raise ValidationError(location, "Origin and destination must be strings.")
        if not origin.strip() or not destination.strip():
            raise ValidationError(location, "Origin and destination must be provided.")

    def _perform_distance_lookup(
        self,
        *,
        origin: str,
        destination: str,
        mode: TravelMode,
        metric: OptimizeFor,
        cache_key: str,
        cancellation_token: CancellationToken | None,
        location: str,
    ) -> float:
        """Execute a single outbound distance-matrix request and cache the parsed result.

        Keeps the retry-wrapped work unit small and explicit."""
        if cancellation_token is not None:
            cancellation_token.raise_if_cancelled(location)
        data = self._request_json(
            self._config.google_maps.distance_matrix_url,
            self._distance_matrix_params(
                base={
                    "origins": origin,
                    "destinations": destination,
                    "mode": mode.value,
                    "key": self._api_key(location),
                },
                mode=mode,
                metric=metric,
            ),
            cancellation_token=cancellation_token,
        )
        value = parse_distance_matrix_value(
            data,
            metric=metric,
            use_duration_in_traffic=self._use_duration_in_traffic(mode=mode, metric=metric),
            location=location,
        )
        self._cache.set(cache_key, value)
        return value

    def _log_distance_lookup_failure(
        self,
        *,
        exc: ExternalServiceError,
        origin: str,
        destination: str,
        mode: TravelMode,
        metric: OptimizeFor,
        departure_time: str | None,
        traffic_model: str | None,
    ) -> None:
        """Emit the structured log payload for a failed single-distance lookup.

        Keeps the structured logging payload separate from the main request path."""
        use_duration_in_traffic = self._use_duration_in_traffic(mode=mode, metric=metric)
        logger.error(
            "Distance lookup failed",
            extra={
                "error_code": error_code_for_exception(exc).value,
                "origin": self._redact_address(origin),
                "destination": self._redact_address(destination),
                "mode": mode.value,
                "metric": metric.value,
                "traffic_aware_time_enabled": bool(self._config.google_maps.traffic_aware_time),
                "use_duration_in_traffic": use_duration_in_traffic,
                "departure_time": departure_time,
                "traffic_model": traffic_model,
                "route_cache_variant": self.get_route_cache_key(mode=mode, metric=metric),
            },
        )

    def _validate_matrix_inputs(
        self,
        *,
        location: str,
        addresses: Sequence[str],
        cancellation_token: CancellationToken | None,
        max_seconds: float,
    ) -> None:
        """Validate the inputs for a full matrix build request.

        Keeps build_matrix focused on orchestration rather than pre-flight validation."""
        if not addresses:
            raise ValidationError(location, "Addresses are required for matrix build.")
        if any(not isinstance(address, str) or not address.strip() for address in addresses):
            raise ValidationError(location, "Every matrix address must be a non empty string.")
        if any("|" in address for address in addresses):
            raise ValidationError(location, "Matrix addresses must not contain the pipe separator.")
        if len(addresses) ** 2 > _MAX_LEGACY_MATRIX_ELEMENTS:
            raise ValidationError(
                location,
                f"Matrix request exceeds the {_MAX_LEGACY_MATRIX_ELEMENTS}-element API limit.",
            )
        if max_seconds <= 0:
            raise ValidationError(location, "max_seconds must be positive.")
        if cancellation_token is None:
            raise ValidationError(location, "cancellation_token is required.")
