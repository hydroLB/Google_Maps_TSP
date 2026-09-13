"""Network-free Google Maps client substitute for the interactive demo."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import OptimizeFor, TravelMode

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.shared.cancellation import CancellationToken


@dataclass(frozen=True, slots=True)
class DemoLandmark:
    """A disclosed canonical address and coordinate used by the offline demo."""

    name: str
    latitude: float
    longitude: float
    aliases: tuple[str, ...] = ()


DEMO_LANDMARKS: tuple[DemoLandmark, ...] = (
    DemoLandmark(
        "Grand Central Terminal, 89 E 42nd St, New York, NY 10017",
        40.752726,
        -73.977229,
        ("Grand Central Terminal", "Grand Central"),
    ),
    DemoLandmark(
        "Empire State Building, 20 W 34th St, New York, NY 10001",
        40.748441,
        -73.985664,
        ("Empire State Building",),
    ),
    DemoLandmark(
        "Flatiron Building, 175 5th Ave, New York, NY 10010",
        40.741061,
        -73.989699,
        ("Flatiron Building",),
    ),
    DemoLandmark(
        "Washington Square Park, Washington Square, New York, NY 10012",
        40.730823,
        -73.997332,
        ("Washington Square Park",),
    ),
    DemoLandmark(
        "Brooklyn Bridge, New York, NY 10038",
        40.706086,
        -73.996864,
        ("Brooklyn Bridge",),
    ),
    DemoLandmark(
        "The Metropolitan Museum of Art, 1000 5th Ave, New York, NY 10028",
        40.779437,
        -73.963244,
        ("Metropolitan Museum of Art", "The Met"),
    ),
)

DEMO_PREFILL_ADDRESSES: tuple[str, str, str, str, str] = (
    DEMO_LANDMARKS[0].name,
    DEMO_LANDMARKS[1].name,
    DEMO_LANDMARKS[2].name,
    DEMO_LANDMARKS[3].name,
    DEMO_LANDMARKS[4].name,
)

_EARTH_RADIUS_KM = 6371.0088
_ROAD_DISTANCE_FACTOR: dict[TravelMode, float] = {
    TravelMode.DRIVING: 1.28,
    TravelMode.WALKING: 1.18,
    TravelMode.BICYCLING: 1.22,
    TravelMode.TRANSIT: 1.32,
}
_AVERAGE_SPEED_KPH: dict[TravelMode, float] = {
    TravelMode.DRIVING: 24.0,
    TravelMode.WALKING: 4.8,
    TravelMode.BICYCLING: 15.0,
    TravelMode.TRANSIT: 19.0,
}


class DemoMapsClient(GoogleMapsClient):
    """Serve deterministic NYC landmark data without constructing an HTTP session."""

    def __init__(self) -> None:
        # Deliberately do not call GoogleMapsClient.__init__: it constructs requests.Session.
        self._landmarks_by_input = {
            candidate.casefold(): landmark
            for landmark in DEMO_LANDMARKS
            for candidate in (landmark.name, *landmark.aliases)
        }

    def has_api_key(self) -> bool:
        """Return true so offline startup never prompts for Google credentials."""

        return True

    def set_api_key(self, api_key: str) -> None:
        """Validate the UI input while retaining network-free demo behavior."""

        location = "fastest_route.infrastructure.demo.maps_client.DemoMapsClient.set_api_key"
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValidationError(location, "api_key must be a non-empty string.")

    def close(self) -> None:
        """Release resources (the demo client intentionally owns none)."""

    def geocode(
        self,
        address: str,
        *,
        select_callback: Callable[[Sequence[str]], str | None] | None = None,
    ) -> str:
        """Resolve a fixture name or alias to its canonical disclosed address."""

        location = "fastest_route.infrastructure.demo.maps_client.DemoMapsClient.geocode"
        if not isinstance(address, str) or not address.strip():
            raise ValidationError(location, "Address must be a non-empty string.")
        if select_callback is not None and not callable(select_callback):
            raise ValidationError(location, "select_callback must be callable when provided.")
        landmark = self._landmarks_by_input.get(address.strip().casefold())
        if landmark is None:
            raise ValidationError(
                location,
                "Address is not available offline. Choose one of the demo landmark suggestions.",
            )
        return landmark.name

    def autocomplete(self, query: str) -> list[str]:
        """Return canonical fixture addresses matching a name, address, or alias."""

        location = "fastest_route.infrastructure.demo.maps_client.DemoMapsClient.autocomplete"
        if not isinstance(query, str) or not query.strip():
            raise ValidationError(location, "Autocomplete query must be a non-empty string.")
        needle = query.strip().casefold()
        return [
            landmark.name
            for landmark in DEMO_LANDMARKS
            if any(
                needle in candidate.casefold() for candidate in (landmark.name, *landmark.aliases)
            )
        ]

    def build_matrix(
        self,
        addresses: Sequence[str],
        mode: TravelMode,
        metric: OptimizeFor,
        *,
        cancellation_token: CancellationToken,
        max_seconds: float,
    ) -> list[list[float]]:
        """Build a deterministic distance-km or duration-minute matrix from fixtures."""

        location = "fastest_route.infrastructure.demo.maps_client.DemoMapsClient.build_matrix"
        if not isinstance(mode, TravelMode):
            raise ValidationError(location, "mode must be a TravelMode.")
        if not isinstance(metric, OptimizeFor):
            raise ValidationError(location, "metric must be an OptimizeFor.")
        if cancellation_token is None:
            raise ValidationError(location, "cancellation_token is required.")
        if isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float)):
            raise ValidationError(location, "max_seconds must be numeric.")
        if not math.isfinite(float(max_seconds)) or max_seconds <= 0:
            raise ValidationError(location, "max_seconds must be finite and greater than zero.")
        cancellation_token.raise_if_cancelled(location)
        landmarks = [self._resolve_landmark(address, location=location) for address in addresses]
        if not landmarks:
            raise ValidationError(location, "At least one demo address is required.")

        matrix: list[list[float]] = []
        for row_index, origin in enumerate(landmarks):
            cancellation_token.raise_if_cancelled(location)
            row: list[float] = []
            for column_index, destination in enumerate(landmarks):
                cancellation_token.raise_if_cancelled(location)
                if row_index == column_index:
                    row.append(0.0)
                    continue
                distance_km = self._haversine_km(origin, destination) * _ROAD_DISTANCE_FACTOR[mode]
                value = (
                    distance_km
                    if metric == OptimizeFor.DISTANCE
                    else distance_km / _AVERAGE_SPEED_KPH[mode] * 60.0
                )
                row.append(round(value, 3))
            matrix.append(row)
        return matrix

    def get_route_cache_key(self, *, mode: TravelMode, metric: OptimizeFor) -> str:
        """Return a stable cache variant for deterministic demo estimates."""

        location = (
            "fastest_route.infrastructure.demo.maps_client.DemoMapsClient.get_route_cache_key"
        )
        if not isinstance(mode, TravelMode):
            raise ValidationError(location, "mode must be a TravelMode.")
        if not isinstance(metric, OptimizeFor):
            raise ValidationError(location, "metric must be an OptimizeFor.")
        return f"offline-demo-v1|{mode.value}|{metric.value}"

    def _resolve_landmark(self, address: object, *, location: str) -> DemoLandmark:
        if not isinstance(address, str) or not address.strip():
            raise ValidationError(location, "Every address must be a non-empty string.")
        landmark = self._landmarks_by_input.get(address.strip().casefold())
        if landmark is None:
            raise ValidationError(
                location,
                f"Address {address!r} is not in the offline demo fixture.",
            )
        return landmark

    @staticmethod
    def _haversine_km(origin: DemoLandmark, destination: DemoLandmark) -> float:
        origin_latitude = math.radians(origin.latitude)
        destination_latitude = math.radians(destination.latitude)
        latitude_delta = destination_latitude - origin_latitude
        longitude_delta = math.radians(destination.longitude - origin.longitude)
        haversine = (
            math.sin(latitude_delta / 2.0) ** 2
            + math.cos(origin_latitude)
            * math.cos(destination_latitude)
            * math.sin(longitude_delta / 2.0) ** 2
        )
        return _EARTH_RADIUS_KM * 2.0 * math.asin(math.sqrt(haversine))


__all__ = [
    "DEMO_LANDMARKS",
    "DEMO_PREFILL_ADDRESSES",
    "DemoLandmark",
    "DemoMapsClient",
]
