from __future__ import annotations

from pathlib import Path

import pytest

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
from fastest_route.shared.errors import ConfigError
from fastest_route.shared.types import OptimizeFor, TrafficModel, TravelMode


def test_google_maps_config_requires_key_when_not_test() -> None:
    config = GoogleMapsConfig(
        api_key="",
        distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
        geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
        places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
        traffic_aware_time=False,
        departure_time="now",
        traffic_model=TrafficModel.BEST_GUESS,
    )
    with pytest.raises(ConfigError):
        config.validate(allow_empty_key=False)


def test_google_maps_config_traffic_aware_requires_valid_departure_time() -> None:
    config = GoogleMapsConfig(
        api_key="key",
        distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
        geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
        places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
        traffic_aware_time=True,
        departure_time="soon",
        traffic_model=TrafficModel.BEST_GUESS,
    )
    with pytest.raises(ConfigError):
        config.validate(allow_empty_key=True)


def test_google_maps_config_traffic_aware_rejects_negative_departure_time() -> None:
    config = GoogleMapsConfig(
        api_key="key",
        distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
        geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
        places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
        traffic_aware_time=True,
        departure_time="-1",
        traffic_model=TrafficModel.BEST_GUESS,
    )
    with pytest.raises(ConfigError):
        config.validate(allow_empty_key=True)


def test_google_maps_config_traffic_aware_rejects_empty_departure_time() -> None:
    config = GoogleMapsConfig(
        api_key="key",
        distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
        geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
        places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
        traffic_aware_time=True,
        departure_time=" ",
        traffic_model=TrafficModel.BEST_GUESS,
    )
    with pytest.raises(ConfigError):
        config.validate(allow_empty_key=True)


def test_google_maps_config_traffic_aware_rejects_invalid_traffic_model_type() -> None:
    config = GoogleMapsConfig(
        api_key="key",
        distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
        geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
        places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
        traffic_aware_time=True,
        departure_time="now",
        traffic_model="best_guess",  # type: ignore[arg-type]
    )
    with pytest.raises(ConfigError):
        config.validate(allow_empty_key=True)


def test_app_config_allows_empty_google_maps_key_in_dev() -> None:
    app = AppConfig(
        environment="dev",
        google_maps=GoogleMapsConfig(
            api_key="",
            distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
            geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
            places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ),
        cache=CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ),
        routing=RoutingConfig(
            max_exact=3,
            two_opt_max_passes=1,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=1.0,
        ),
        http=HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.1,
            retry_jitter_ratio=0.0,
            retry_statuses=(429,),
        ),
        rate_limit=RateLimitConfig(
            requests_per_second=1.0,
            burst=1,
            max_wait_seconds=1.0,
        ),
        logging=LoggingConfig(level="INFO"),
        ui=UiConfig(
            min_stops=3,
            max_stops=3,
            autocomplete_min_chars=3,
            autocomplete_delay_ms=10,
            status_delay_ms=10,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ),
    )
    app.validate()


def test_app_config_requires_google_maps_key_in_prod() -> None:
    app = AppConfig(
        environment="prod",
        google_maps=GoogleMapsConfig(
            api_key="",
            distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
            geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
            places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ),
        cache=CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ),
        routing=RoutingConfig(
            max_exact=3,
            two_opt_max_passes=1,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=1.0,
        ),
        http=HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.1,
            retry_jitter_ratio=0.0,
            retry_statuses=(429,),
        ),
        rate_limit=RateLimitConfig(
            requests_per_second=1.0,
            burst=1,
            max_wait_seconds=1.0,
        ),
        logging=LoggingConfig(level="INFO"),
        ui=UiConfig(
            min_stops=3,
            max_stops=3,
            autocomplete_min_chars=3,
            autocomplete_delay_ms=10,
            status_delay_ms=10,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ),
    )
    with pytest.raises(ConfigError):
        app.validate()


def test_google_maps_config_missing_urls_raise() -> None:
    base = {
        "api_key": "key",
        "distance_matrix_url": "https://maps.googleapis.com/maps/api/distancematrix/json",
        "geocode_url": "https://maps.googleapis.com/maps/api/geocode/json",
        "places_autocomplete_url": "https://maps.googleapis.com/maps/api/place/autocomplete/json",
    }
    with pytest.raises(ConfigError):
        GoogleMapsConfig(
            api_key=base["api_key"],
            distance_matrix_url="",
            geocode_url=base["geocode_url"],
            places_autocomplete_url=base["places_autocomplete_url"],
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ).validate(allow_empty_key=True)
    with pytest.raises(ConfigError):
        GoogleMapsConfig(
            api_key=base["api_key"],
            distance_matrix_url=base["distance_matrix_url"],
            geocode_url="",
            places_autocomplete_url=base["places_autocomplete_url"],
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ).validate(allow_empty_key=True)
    with pytest.raises(ConfigError):
        GoogleMapsConfig(
            api_key=base["api_key"],
            distance_matrix_url=base["distance_matrix_url"],
            geocode_url=base["geocode_url"],
            places_autocomplete_url="",
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ).validate(allow_empty_key=True)


@pytest.mark.parametrize(
    "invalid_url",
    [
        "http://maps.googleapis.com/maps/api/geocode/json",
        "https://attacker.invalid/maps/api/geocode/json",
        "https://user@maps.googleapis.com/maps/api/geocode/json",
        "https://maps.googleapis.com:444/maps/api/geocode/json",
        "https://maps.googleapis.com/maps/api/geocode/json?key=embedded",
    ],
)
def test_google_maps_config_rejects_unsafe_credential_endpoints(invalid_url: str) -> None:
    config = GoogleMapsConfig(
        api_key="key",
        distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
        geocode_url=invalid_url,
        places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
        traffic_aware_time=False,
        departure_time="now",
        traffic_model=TrafficModel.BEST_GUESS,
    )

    with pytest.raises(ConfigError, match="maps.googleapis.com"):
        config.validate(allow_empty_key=True)


def test_cache_config_invalid_sizes() -> None:
    config = CacheConfig(
        disk_path=Path("/tmp/cache.json"),
        geocode_disk_path=None,
        route_cache_size=0,
        disk_cache_ttl_seconds=1,
        geocode_cache_size=1,
        geocode_disk_cache_ttl_seconds=1,
    )
    with pytest.raises(ConfigError):
        config.validate()


def test_cache_config_other_invalid_fields() -> None:
    with pytest.raises(ConfigError):
        CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=0,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ).validate()
    with pytest.raises(ConfigError):
        CacheConfig(
            disk_path=Path(" "),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ).validate()
    with pytest.raises(ConfigError):
        CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=0,
            geocode_disk_cache_ttl_seconds=1,
        ).validate()
    with pytest.raises(ConfigError):
        CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=0,
        ).validate()
    with pytest.raises(ConfigError):
        CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=Path(" "),
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ).validate()


def test_routing_config_invalid_values() -> None:
    config = RoutingConfig(
        max_exact=1,
        two_opt_max_passes=0,
        nearest_neighbor_start_index=-1,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=0.0,
    )
    with pytest.raises(ConfigError):
        config.validate()


def test_routing_config_invalid_fields_individual() -> None:
    with pytest.raises(ConfigError):
        RoutingConfig(
            max_exact=2,
            two_opt_max_passes=0,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=1.0,
        ).validate()
    with pytest.raises(ConfigError):
        RoutingConfig(
            max_exact=2,
            two_opt_max_passes=1,
            nearest_neighbor_start_index=-1,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=1.0,
        ).validate()
    with pytest.raises(ConfigError):
        RoutingConfig(
            max_exact=2,
            two_opt_max_passes=1,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=0.0,
        ).validate()


def test_http_config_invalid_values() -> None:
    config = HttpConfig(
        timeout_seconds=0.0,
        retry_max_attempts=0,
        retry_base_delay_seconds=0.0,
        retry_max_delay_seconds=0.0,
        retry_jitter_ratio=2.0,
        retry_statuses=(500,),
    )
    with pytest.raises(ConfigError):
        config.validate()


def test_http_config_invalid_fields_individual() -> None:
    with pytest.raises(ConfigError):
        HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=0,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.2,
            retry_jitter_ratio=0.0,
            retry_statuses=(500,),
        ).validate()
    with pytest.raises(ConfigError):
        HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.0,
            retry_max_delay_seconds=0.2,
            retry_jitter_ratio=0.0,
            retry_statuses=(500,),
        ).validate()
    with pytest.raises(ConfigError):
        HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.0,
            retry_jitter_ratio=0.0,
            retry_statuses=(500,),
        ).validate()
    with pytest.raises(ConfigError):
        HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.2,
            retry_jitter_ratio=2.0,
            retry_statuses=(500,),
        ).validate()


def test_rate_limit_config_invalid_values() -> None:
    config = RateLimitConfig(requests_per_second=0.0, burst=0, max_wait_seconds=0.0)
    with pytest.raises(ConfigError):
        config.validate()


def test_rate_limit_config_invalid_burst() -> None:
    config = RateLimitConfig(requests_per_second=1.0, burst=0, max_wait_seconds=1.0)
    with pytest.raises(ConfigError):
        config.validate()


def test_rate_limit_config_invalid_max_wait() -> None:
    config = RateLimitConfig(requests_per_second=1.0, burst=1, max_wait_seconds=0.0)
    with pytest.raises(ConfigError):
        config.validate()


def test_logging_config_invalid_level() -> None:
    with pytest.raises(ConfigError):
        LoggingConfig(level=" ").validate()


def test_ui_config_invalid_values() -> None:
    config = UiConfig(
        min_stops=0,
        max_stops=1,
        autocomplete_min_chars=0,
        autocomplete_delay_ms=0,
        status_delay_ms=0,
        theme_mode="system",
        os_theme_poll_seconds=2.0,
    )
    with pytest.raises(ConfigError):
        config.validate()


def test_ui_config_invalid_fields_individual() -> None:
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=0,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ).validate()
    with pytest.raises(ConfigError, match="8 or less"):
        UiConfig(
            min_stops=1,
            max_stops=9,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ).validate()
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=1,
            autocomplete_min_chars=0,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ).validate()
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=1,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=0,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ).validate()
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=1,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=0,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ).validate()


def test_ui_config_rejects_invalid_theme_settings() -> None:
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=1,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="nope",
            os_theme_poll_seconds=2.0,
        ).validate()
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=1,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=0.1,
        ).validate()
    with pytest.raises(ConfigError):
        UiConfig(
            min_stops=1,
            max_stops=1,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=120.0,
        ).validate()


def test_ui_config_accepts_auto_theme_mode() -> None:
    UiConfig(
        min_stops=1,
        max_stops=1,
        autocomplete_min_chars=1,
        autocomplete_delay_ms=1,
        status_delay_ms=1,
        theme_mode="auto",
        os_theme_poll_seconds=2.0,
    ).validate()


def test_app_config_validate_allows_test_env() -> None:
    config = AppConfig(
        environment="test",
        google_maps=GoogleMapsConfig(
            api_key="",
            distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
            geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
            places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ),
        cache=CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ),
        routing=RoutingConfig(
            max_exact=2,
            two_opt_max_passes=1,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=1.0,
        ),
        http=HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.2,
            retry_jitter_ratio=0.0,
            retry_statuses=(500,),
        ),
        rate_limit=RateLimitConfig(requests_per_second=1.0, burst=1, max_wait_seconds=1.0),
        logging=LoggingConfig(level="INFO"),
        ui=UiConfig(
            min_stops=1,
            max_stops=2,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ),
    )
    config.validate()


def test_app_config_requires_environment() -> None:
    config = AppConfig(
        environment=" ",
        google_maps=GoogleMapsConfig(
            api_key="",
            distance_matrix_url="https://maps.googleapis.com/maps/api/distancematrix/json",
            geocode_url="https://maps.googleapis.com/maps/api/geocode/json",
            places_autocomplete_url="https://maps.googleapis.com/maps/api/place/autocomplete/json",
            traffic_aware_time=False,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ),
        cache=CacheConfig(
            disk_path=Path("/tmp/cache.json"),
            geocode_disk_path=None,
            route_cache_size=1,
            disk_cache_ttl_seconds=1,
            geocode_cache_size=1,
            geocode_disk_cache_ttl_seconds=1,
        ),
        routing=RoutingConfig(
            max_exact=2,
            two_opt_max_passes=1,
            nearest_neighbor_start_index=0,
            default_mode=TravelMode.DRIVING,
            default_optimize_for=OptimizeFor.TIME,
            max_compute_seconds=1.0,
        ),
        http=HttpConfig(
            timeout_seconds=1.0,
            retry_max_attempts=1,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=0.2,
            retry_jitter_ratio=0.0,
            retry_statuses=(500,),
        ),
        rate_limit=RateLimitConfig(requests_per_second=1.0, burst=1, max_wait_seconds=1.0),
        logging=LoggingConfig(level="INFO"),
        ui=UiConfig(
            min_stops=1,
            max_stops=2,
            autocomplete_min_chars=1,
            autocomplete_delay_ms=1,
            status_delay_ms=1,
            theme_mode="system",
            os_theme_poll_seconds=2.0,
        ),
    )
    with pytest.raises(ConfigError):
        config.validate()
