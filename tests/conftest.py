from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastest_route.config.registry import AppConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "TSP_GOOGLE_MAPS"))


@pytest.fixture()
def app_config(tmp_path: Path) -> AppConfig:
    from fastest_route.config.registry import (
        AppConfig,
        CacheConfig,
        GoogleMapsConfig,
        HttpConfig,
        LoggingConfig,
        RateLimitConfig,
        RoutingConfig,
        UiConfig,
    )
    from fastest_route.shared.types import OptimizeFor, TrafficModel, TravelMode

    config = AppConfig(
        environment="test",
        google_maps=GoogleMapsConfig(
            api_key="test-key",
            distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
            geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
            places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ),
        cache=CacheConfig(
            disk_path=tmp_path / "distance_cache.json",
            geocode_disk_path=None,
            route_cache_size=50,
            disk_cache_ttl_seconds=3600,
            geocode_cache_size=200,
            geocode_disk_cache_ttl_seconds=3600,
        ),
        routing=RoutingConfig(
            max_exact=7,
            two_opt_max_passes=5,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=5.0,
        ),
        http=HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=2,
            retry_base_delay_seconds=0.01,
            retry_max_delay_seconds=0.05,
            retry_jitter_ratio=0.0,
            retry_statuses=(429, 500, 502, 503, 504),
        ),
        rate_limit=RateLimitConfig(
            requests_per_second=1000.0,
            burst=1000,
            max_wait_seconds=1.0,
        ),
        logging=LoggingConfig(level="INFO"),
        ui=UiConfig(
            min_stops=3,
            max_stops=7,
            autocomplete_min_chars=3,
            autocomplete_delay_ms=50,
            status_delay_ms=50,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ),
    )
    config.validate()
    return config
