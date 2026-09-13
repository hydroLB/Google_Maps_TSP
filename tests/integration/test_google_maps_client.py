from __future__ import annotations

import importlib
import json
from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
import requests

from fastest_route.infrastructure.cache.distance_cache import DistanceCache
from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache
from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
from fastest_route.infrastructure.rate_limit import RateLimiter
from fastest_route.infrastructure.retry import RetryPolicy
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import (
    CancellationError,
    DeadlineExceededError,
    ExternalServiceError,
    ValidationError,
)
from fastest_route.shared.types import OptimizeFor, TrafficModel, TravelMode

if TYPE_CHECKING:
    from pathlib import Path

    from fastest_route.config.registry import AppConfig

client_module = importlib.import_module("fastest_route.infrastructure.google_maps.client")
traffic_module = importlib.import_module(
    "fastest_route.infrastructure.google_maps.client_support.traffic"
)


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


def test_get_distance_time(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "rows": [
                    {
                        "elements": [
                            {
                                "status": "OK",
                                "duration": {"value": 600},
                                "distance": {"value": 12000},
                            }
                        ]
                    }
                ],
            },
        )
    )
    client._session = mock_session
    minutes = client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)
    assert minutes == 10.0


def test_get_distance_time_traffic_aware_uses_duration_in_traffic(
    app_config: AppConfig, tmp_path: Path
) -> None:
    cfg = replace(
        app_config,
        google_maps=replace(
            app_config.google_maps,
            traffic_aware_time=True,
            departure_time="now",
            traffic_model=TrafficModel.BEST_GUESS,
        ),
    )
    client = _build_client(cfg, tmp_path / "cache.json")
    captured: dict[str, object] = {}

    def fake_get(url: str, params: dict[str, str], timeout: float):
        captured["url"] = url
        captured["params"] = dict(params)
        return FakeResponse(
            200,
            {
                "status": "OK",
                "rows": [
                    {
                        "elements": [
                            {
                                "status": "OK",
                                "duration": {"value": 600},
                                "duration_in_traffic": {"value": 900},
                                "distance": {"value": 12000},
                            }
                        ]
                    }
                ],
            },
        )

    mock_session = Mock()
    mock_session.get = Mock(side_effect=fake_get)
    client._session = mock_session
    minutes = client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)
    assert minutes == 15.0
    assert isinstance(captured.get("params"), dict)
    params = captured["params"]
    assert params["departure_time"] == "now"
    assert params["traffic_model"] == "best_guess"
    assert client.get_route_cache_key(mode=TravelMode.DRIVING, metric=OptimizeFor.TIME).startswith(
        "traffic="
    )


def test_live_traffic_cache_variant_is_bounded_by_time_bucket(
    app_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live traffic results should expire across five-minute cache buckets."""

    cfg = replace(
        app_config,
        google_maps=replace(
            app_config.google_maps,
            traffic_aware_time=True,
            departure_time="now",
        ),
    )
    client = _build_client(cfg, tmp_path / "cache.json")
    monkeypatch.setattr(traffic_module.time, "time", lambda: 60.0)
    first = client.get_route_cache_key(mode=TravelMode.DRIVING, metric=OptimizeFor.TIME)
    monkeypatch.setattr(traffic_module.time, "time", lambda: 361.0)
    second = client.get_route_cache_key(mode=TravelMode.DRIVING, metric=OptimizeFor.TIME)
    assert first != second
    assert "now@" in first


def test_api_key_override_enables_requests(app_config: AppConfig, tmp_path: Path) -> None:
    cfg = replace(app_config, google_maps=replace(app_config.google_maps, api_key=""))
    client = _build_client(cfg, tmp_path / "cache.json")
    assert client.has_api_key() is False
    client.set_api_key("runtime-key")
    assert client.has_api_key() is True


def test_geocode_caches_results(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "results": [{"formatted_address": "Resolved A"}],
            },
        )
    )
    client._session = mock_session
    assert client.geocode("A") == "Resolved A"
    assert client.geocode("A") == "Resolved A"
    assert mock_session.get.call_count == 1


def test_get_distance_distance(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "rows": [
                    {
                        "elements": [
                            {
                                "status": "OK",
                                "duration": {"value": 300},
                                "distance": {"value": 5000},
                            }
                        ]
                    }
                ],
            },
        )
    )
    client._session = mock_session
    kilometers = client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.DISTANCE)
    assert kilometers == 5.0


def test_geocode_selection(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "results": [
                    {"formatted_address": "Option One"},
                    {"formatted_address": "Option Two"},
                ],
            },
        )
    )
    client._session = mock_session

    def select(options: list[str]) -> str | None:
        return options[1]

    result = client.geocode("Some Place", select_callback=select)
    assert result == "Option Two"


def test_autocomplete_suggestions(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "predictions": [{"description": "Alpha"}, {"description": "Beta"}],
            },
        )
    )
    client._session = mock_session
    suggestions = client.autocomplete("Al")
    assert suggestions == ["Alpha", "Beta"]


def test_get_distance_uses_cache(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "rows": [
                    {
                        "elements": [
                            {
                                "status": "OK",
                                "duration": {"value": 120},
                                "distance": {"value": 1000},
                            }
                        ]
                    }
                ],
            },
        )
    )
    client._session = mock_session
    first = client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)
    second = client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)
    assert first == second
    assert mock_session.get.call_count == 1


def test_build_matrix_cancellation(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "rows": [
                    {
                        "elements": [
                            {
                                "status": "OK",
                                "duration": {"value": 120},
                                "distance": {"value": 1000},
                            }
                        ]
                    }
                ],
            },
        )
    )
    client._session = mock_session
    token = CancellationToken()
    token.cancel()
    with pytest.raises(CancellationError):
        client.build_matrix(
            ["A", "B"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=token,
            max_seconds=1.0,
        )


def test_build_matrix_batches_request_and_reuses_leg_cache(
    app_config: AppConfig, tmp_path: Path
) -> None:
    """A square matrix should require one API request and zero requests on a warm cache."""

    client = _build_client(app_config, tmp_path / "cache.json")
    response = FakeResponse(
        200,
        {
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 0}},
                        {"status": "OK", "duration": {"value": 120}},
                    ]
                },
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 180}},
                        {"status": "OK", "duration": {"value": 0}},
                    ]
                },
            ],
        },
    )
    mock_session = Mock()
    mock_session.get = Mock(return_value=response)
    client._session = mock_session

    first = client.build_matrix(
        ["A", "B"],
        TravelMode.DRIVING,
        OptimizeFor.TIME,
        cancellation_token=CancellationToken(),
        max_seconds=1.0,
    )
    second = client.build_matrix(
        ["A", "B"],
        TravelMode.DRIVING,
        OptimizeFor.TIME,
        cancellation_token=CancellationToken(),
        max_seconds=1.0,
    )

    assert first == second == [[0.0, 2.0], [3.0, 0.0]]
    assert mock_session.get.call_count == 1
    params = mock_session.get.call_args.kwargs["params"]
    assert params["origins"] == "A|B"
    assert params["destinations"] == "A|B"


@pytest.mark.parametrize(
    "diagonal_element",
    [
        "invalid",
        {"status": "NOT_FOUND", "duration": {"value": 0}},
        {"status": "OK"},
    ],
)
def test_build_matrix_rejects_invalid_diagonal_without_caching_legs(
    app_config: AppConfig,
    tmp_path: Path,
    diagonal_element: object,
) -> None:
    """No directed leg is cached when any diagonal provider element is invalid."""

    client = _build_client(app_config, tmp_path / "cache.json")
    response = FakeResponse(
        200,
        {
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        diagonal_element,
                        {"status": "OK", "duration": {"value": 120}},
                    ]
                },
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 180}},
                        {"status": "OK", "duration": {"value": 0}},
                    ]
                },
            ],
        },
    )
    mock_session = Mock()
    mock_session.get = Mock(return_value=response)
    client._session = mock_session

    with pytest.raises(ExternalServiceError):
        client.build_matrix(
            ["A", "B"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=1.0,
        )

    assert client._cache._data == {}


def test_build_matrix_retries_transient_provider_status(
    app_config: AppConfig, tmp_path: Path
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    success = FakeResponse(
        200,
        {
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 0}},
                        {"status": "OK", "duration": {"value": 120}},
                    ]
                },
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 180}},
                        {"status": "OK", "duration": {"value": 0}},
                    ]
                },
            ],
        },
    )
    mock_session = Mock()
    mock_session.get.side_effect = [
        FakeResponse(200, {"status": "UNKNOWN_ERROR"}),
        success,
    ]
    client._session = mock_session

    matrix = client.build_matrix(
        ["A", "B"],
        TravelMode.DRIVING,
        OptimizeFor.TIME,
        cancellation_token=CancellationToken(),
        max_seconds=2.0,
    )

    assert matrix == [[0.0, 2.0], [3.0, 0.0]]
    assert mock_session.get.call_count == 2


def test_build_matrix_clamps_http_timeout_and_discards_late_response(
    app_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    clock = {"now": 0.0}
    monkeypatch.setattr(client_module.time, "monotonic", lambda: clock["now"])

    response = FakeResponse(
        200,
        {
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 0}},
                        {"status": "OK", "duration": {"value": 120}},
                    ]
                },
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 180}},
                        {"status": "OK", "duration": {"value": 0}},
                    ]
                },
            ],
        },
    )

    def late_get(*_args: object, **_kwargs: object) -> FakeResponse:
        clock["now"] = 0.2
        return response

    mock_session = Mock()
    mock_session.get.side_effect = late_get
    client._session = mock_session

    with pytest.raises(DeadlineExceededError, match="Matrix build exceeded"):
        client.build_matrix(
            ["A", "B"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=0.1,
        )

    timeout = mock_session.get.call_args.kwargs["timeout"]
    assert 0 < timeout <= 0.1
    assert client._cache._data == {}


def test_get_distance_raises_on_bad_status(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(return_value=FakeResponse(500, {"status": "ERROR"}))
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)
    assert mock_session.get.call_count == app_config.http.retry_max_attempts


def test_malformed_request_configuration_is_not_retried(
    app_config: AppConfig, tmp_path: Path
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get.side_effect = requests.exceptions.MissingSchema("bad URL")
    client._session = mock_session

    with pytest.raises(ExternalServiceError, match="configuration was invalid"):
        client.autocomplete("Boston")

    assert mock_session.get.call_count == 1


def test_autocomplete_rejects_empty_query(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.autocomplete(" ")


def test_geocode_requires_callback_for_multiple_results(
    app_config: AppConfig, tmp_path: Path
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "results": [
                    {"formatted_address": "Option One"},
                    {"formatted_address": "Option Two"},
                ],
            },
        )
    )
    client._session = mock_session
    with pytest.raises(ValidationError):
        client.geocode("Some Place", select_callback=None)


def test_request_json_rejects_bad_json(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")

    class BadJsonResponse:
        status_code = 200
        text = "{bad-json"

    mock_session = Mock()
    mock_session.get = Mock(return_value=BadJsonResponse())
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)


def test_request_json_rejects_non_mapping(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")

    class ListResponse:
        status_code = 200
        text = "[]"

    mock_session = Mock()
    mock_session.get = Mock(return_value=ListResponse())
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.autocomplete("Alpha")


def test_request_json_handles_http_errors(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(side_effect=requests.RequestException("boom"))
    client._session = mock_session
    with pytest.raises(ExternalServiceError) as exc_info:
        client.autocomplete("Alpha")
    assert "[E_EXTERNAL_IO]" in str(exc_info.value)


def test_request_json_rejects_unexpected_status(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(return_value=FakeResponse(404, {"status": "NOT_FOUND"}))
    client._session = mock_session
    with pytest.raises(ExternalServiceError) as exc_info:
        client.autocomplete("Alpha")
    assert "[E_EXTERNAL_IO]" in str(exc_info.value)
    assert mock_session.get.call_count == 1


def test_autocomplete_retries_only_transient_provider_statuses(
    app_config: AppConfig, tmp_path: Path
) -> None:
    """A transient API status is retried, while the successful retry is returned."""

    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        side_effect=[
            FakeResponse(200, {"status": "UNKNOWN_ERROR", "predictions": []}),
            FakeResponse(
                200,
                {"status": "OK", "predictions": [{"description": "Alpha"}]},
            ),
        ]
    )
    client._session = mock_session
    assert client.autocomplete("Alpha") == ["Alpha"]
    assert mock_session.get.call_count == 2


def test_close_raises_on_session_error(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.close = Mock(side_effect=requests.RequestException("boom"))
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.close()


def test_geocode_rejects_empty_input(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.geocode(" ")


def test_geocode_status_error(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(return_value=FakeResponse(200, {"status": "ZERO_RESULTS"}))
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.geocode(
            "Some Place", select_callback=lambda options: options[0] if options else None
        )


def test_geocode_missing_results(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(return_value=FakeResponse(200, {"status": "OK", "results": []}))
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.geocode(
            "Some Place", select_callback=lambda options: options[0] if options else None
        )


def test_geocode_no_formatted_addresses(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(200, {"status": "OK", "results": [{"name": "x"}]})
    )
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.geocode(
            "Some Place", select_callback=lambda options: options[0] if options else None
        )


def test_geocode_selection_empty(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "results": [{"formatted_address": "One"}, {"formatted_address": "Two"}],
            },
        )
    )
    client._session = mock_session
    with pytest.raises(ValidationError):
        client.geocode("Some Place", select_callback=lambda _options: " ")


def test_autocomplete_predictions_not_list(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(return_value=FakeResponse(200, {"status": "OK", "predictions": {}}))
    client._session = mock_session
    assert client.autocomplete("Alpha") == []


def test_get_distance_rejects_empty_addresses(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.get_distance("", "B", TravelMode.DRIVING, OptimizeFor.TIME)


def test_get_distance_missing_rows(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(return_value=FakeResponse(200, {"status": "OK", "rows": []}))
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)


def test_get_distance_element_status_error(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {"status": "OK", "rows": [{"elements": [{"status": "NOT_FOUND"}]}]},
        )
    )
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)


def test_get_distance_missing_duration_payload(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {
                "status": "OK",
                "rows": [{"elements": [{"status": "OK", "distance": {"value": 1000}}]}],
            },
        )
    )
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.TIME)


def test_get_distance_missing_distance_payload(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    mock_session = Mock()
    mock_session.get = Mock(
        return_value=FakeResponse(
            200,
            {"status": "OK", "rows": [{"elements": [{"status": "OK", "duration": {"value": 60}}]}]},
        )
    )
    client._session = mock_session
    with pytest.raises(ExternalServiceError):
        client.get_distance("A", "B", TravelMode.DRIVING, OptimizeFor.DISTANCE)


def test_build_matrix_rejects_invalid_inputs(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.build_matrix(
            [],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        client.build_matrix(
            ["A"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=0.0,
        )
    with pytest.raises(ValidationError):
        client.build_matrix(
            ["A|B", "C"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        client.build_matrix(
            [f"Address {index}" for index in range(11)],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=1.0,
        )


def test_google_maps_client_requires_google_maps_config(
    app_config: AppConfig, tmp_path: Path
) -> None:
    cache = DistanceCache(
        tmp_path / "cache.json", ttl_seconds=app_config.cache.disk_cache_ttl_seconds
    )
    rate_limiter = RateLimiter(
        app_config.rate_limit.requests_per_second,
        app_config.rate_limit.burst,
        app_config.rate_limit.max_wait_seconds,
    )
    retry_policy = RetryPolicy(
        max_attempts=app_config.http.retry_max_attempts,
        base_delay_seconds=app_config.http.retry_base_delay_seconds,
        max_delay_seconds=app_config.http.retry_max_delay_seconds,
        jitter_ratio=app_config.http.retry_jitter_ratio,
        retry_statuses=app_config.http.retry_statuses,
    )

    class BadConfig:
        google_maps = None

    with pytest.raises(ValidationError):
        geocode_cache = GeocodeCache(memory_max_items=1, disk_path=None, disk_ttl_seconds=1)
        GoogleMapsClient(
            config=BadConfig(),
            cache=cache,
            geocode_cache=geocode_cache,
            rate_limiter=rate_limiter,
            retry_policy=retry_policy,
        )


def test_google_maps_client_rejects_invalid_config_type(
    app_config: AppConfig, tmp_path: Path
) -> None:
    cache = DistanceCache(
        tmp_path / "cache.json", ttl_seconds=app_config.cache.disk_cache_ttl_seconds
    )
    rate_limiter = RateLimiter(
        app_config.rate_limit.requests_per_second,
        app_config.rate_limit.burst,
        app_config.rate_limit.max_wait_seconds,
    )
    retry_policy = RetryPolicy(
        max_attempts=app_config.http.retry_max_attempts,
        base_delay_seconds=app_config.http.retry_base_delay_seconds,
        max_delay_seconds=app_config.http.retry_max_delay_seconds,
        jitter_ratio=app_config.http.retry_jitter_ratio,
        retry_statuses=app_config.http.retry_statuses,
    )
    with pytest.raises(ValidationError):
        geocode_cache = GeocodeCache(memory_max_items=1, disk_path=None, disk_ttl_seconds=1)
        GoogleMapsClient(
            config=object(),
            cache=cache,
            geocode_cache=geocode_cache,
            rate_limiter=rate_limiter,
            retry_policy=retry_policy,
        )


def test_redact_address_rejects_non_string(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client._redact_address(123)


def test_redact_address_wraps_hash_error(
    app_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    monkeypatch.setattr(
        client_module.hashlib,
        "sha256",
        lambda *_a, **_k: (_ for _ in ()).throw(AttributeError("boom")),
    )
    with pytest.raises(ValidationError):
        client._redact_address("Alpha")


def test_request_json_rejects_empty_url(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client._request_json("", {})


def test_request_json_wraps_validation_error(
    app_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    monkeypatch.setattr(
        type(client._retry_policy),
        "execute",
        lambda *_a, **_k: (_ for _ in ()).throw(ValidationError("test", "boom")),
    )
    with pytest.raises(ExternalServiceError):
        client._request_json("https://example.com", {"a": "b"})


def test_geocode_rejects_non_string_address(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.geocode(123)


def test_geocode_rejects_invalid_callback(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.geocode("Some Place", select_callback="bad")


def test_autocomplete_rejects_non_string_query(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.autocomplete(123)


def test_autocomplete_wraps_type_error(
    app_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    monkeypatch.setattr(
        client, "_request_json", lambda *_a, **_k: (_ for _ in ()).throw(TypeError("boom"))
    )
    with pytest.raises(ExternalServiceError):
        client.autocomplete("Alpha")


def test_get_distance_rejects_non_string_addresses(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.get_distance(123, "B", TravelMode.DRIVING, OptimizeFor.TIME)


def test_build_matrix_requires_token(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    with pytest.raises(ValidationError):
        client.build_matrix(
            ["A", "B"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=None,
            max_seconds=1.0,
        )


def test_build_matrix_time_exceeded(
    app_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    calls = {"count": 0}

    def fake_monotonic() -> float:
        calls["count"] += 1
        return 0.0 if calls["count"] == 1 else 100.0

    monkeypatch.setattr(client_module.time, "monotonic", fake_monotonic)
    with pytest.raises(ExternalServiceError):
        client.build_matrix(
            ["A", "B"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=1.0,
        )


def test_build_matrix_wraps_type_error(app_config: AppConfig, tmp_path: Path) -> None:
    client = _build_client(app_config, tmp_path / "cache.json")
    client._perform_matrix_lookup = lambda **_kwargs: (_ for _ in ()).throw(TypeError("boom"))
    with pytest.raises(ExternalServiceError):
        client.build_matrix(
            ["A", "B"],
            TravelMode.DRIVING,
            OptimizeFor.TIME,
            cancellation_token=CancellationToken(),
            max_seconds=10.0,
        )
