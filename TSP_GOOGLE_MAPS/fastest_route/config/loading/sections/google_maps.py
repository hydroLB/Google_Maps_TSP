"""Google Maps configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_bool, get_str
from fastest_route.config.loading.parsers import parse_traffic_model
from fastest_route.config.registry import GoogleMapsConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_google_maps_config(
    *, google_section: Mapping[str, object], env: Mapping[str, str], location: str
) -> GoogleMapsConfig:
    """Build a GoogleMapsConfig with environment-variable overrides."""
    api_key = env.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        api_key = get_str(google_section, "api_key", "", location).strip()
    traffic_aware_time = get_bool(google_section, "traffic_aware_time", False, location)
    departure_time = get_str(google_section, "departure_time", "now", location).strip()
    traffic_model_raw = get_str(google_section, "traffic_model", "best_guess", location)
    traffic_model = parse_traffic_model(traffic_model_raw, location=location)
    return GoogleMapsConfig(
        api_key=api_key,
        distance_matrix_url=get_str(
            google_section,
            "distance_matrix_url",
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            location,
        ),
        geocode_url=get_str(
            google_section,
            "geocode_url",
            "https://maps.googleapis.com/maps/api/geocode/json",
            location,
        ),
        places_autocomplete_url=get_str(
            google_section,
            "places_autocomplete_url",
            "https://maps.googleapis.com/maps/api/place/autocomplete/json",
            location,
        ),
        traffic_aware_time=traffic_aware_time,
        departure_time=departure_time,
        traffic_model=traffic_model,
    )
