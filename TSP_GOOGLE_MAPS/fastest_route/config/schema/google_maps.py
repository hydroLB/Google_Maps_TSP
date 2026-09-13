"""Google Maps configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from fastest_route.shared.errors import ConfigError
from fastest_route.shared.types import TrafficModel


@dataclass(frozen=True)
class GoogleMapsConfig:
    """Hold Google Maps API configuration and endpoints."""

    api_key: str
    distance_matrix_url: str
    geocode_url: str
    places_autocomplete_url: str
    traffic_aware_time: bool
    departure_time: str
    traffic_model: TrafficModel

    @staticmethod
    def _validate_endpoint(name: str, value: str) -> None:
        """Require credential-bearing requests to target Google over HTTPS."""

        location = "fastest_route.config.registry.GoogleMapsConfig.validate"
        if not value.strip():
            raise ConfigError(location, f"{name} must be set.")
        try:
            parsed = urlsplit(value.strip())
            port = parsed.port
        except ValueError as exc:
            raise ConfigError(location, f"{name} must be a valid URL.") from exc
        if (
            parsed.scheme.lower() != "https"
            or parsed.hostname != "maps.googleapis.com"
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
            or not parsed.path.startswith("/maps/api/")
            or parsed.query
            or parsed.fragment
        ):
            raise ConfigError(
                location,
                f"{name} must use HTTPS on maps.googleapis.com without credentials, query, or fragment.",
            )

    def validate(self, *, allow_empty_key: bool) -> None:
        """Validate Google Maps configuration fields."""
        location = "fastest_route.config.registry.GoogleMapsConfig.validate"
        self._validate_endpoint("distance_matrix_url", self.distance_matrix_url)
        self._validate_endpoint("geocode_url", self.geocode_url)
        self._validate_endpoint("places_autocomplete_url", self.places_autocomplete_url)
        if not allow_empty_key and not self.api_key.strip():
            raise ConfigError(location, "api_key is required for live requests.")
        if self.traffic_aware_time:
            if not isinstance(self.departure_time, str) or not self.departure_time.strip():
                raise ConfigError(
                    location, "departure_time must be set when traffic_aware_time is enabled."
                )
            departure_value = self.departure_time.strip().lower()
            if departure_value != "now":
                try:
                    parsed = int(departure_value)
                except ValueError as exc:
                    raise ConfigError(
                        location, "departure_time must be 'now' or Unix seconds."
                    ) from exc
                if parsed < 0:
                    raise ConfigError(
                        location, "departure_time must be 'now' or a non negative integer."
                    )
            if not isinstance(self.traffic_model, TrafficModel):
                raise ConfigError(location, "traffic_model must be a TrafficModel.")
