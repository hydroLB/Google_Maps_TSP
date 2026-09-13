"""Tests for the package-native application and command-line entry points."""

from __future__ import annotations

import importlib
import runpy
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from fastest_route import entrypoint
from fastest_route.shared.errors import AppError, ConfigError

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture(autouse=True)
def _isolate_local_environment_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entrypoint, "_load_local_environment", lambda: None)


class _CapturedLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def error(self, message: str, *, extra: dict[str, object]) -> None:
        self.calls.append((message, extra))


def _factory(value: object, calls: list[tuple[tuple[object, ...], dict[str, object]]]) -> Callable:
    def build(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        return value

    return build


def test_build_dependencies_wires_the_runtime_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        logging=SimpleNamespace(level="INFO"),
        cache=SimpleNamespace(
            disk_path="distance.json",
            disk_cache_ttl_seconds=60,
            geocode_cache_size=20,
            geocode_disk_path=None,
            geocode_disk_cache_ttl_seconds=120,
            route_cache_size=10,
        ),
        rate_limit=SimpleNamespace(
            requests_per_second=5.0,
            burst=10,
            max_wait_seconds=2.0,
        ),
        http=SimpleNamespace(
            retry_max_attempts=3,
            retry_base_delay_seconds=0.1,
            retry_max_delay_seconds=1.0,
            retry_jitter_ratio=0.2,
            retry_statuses=(429, 500),
        ),
        routing=object(),
    )
    distance_cache = object()
    geocode_cache = object()
    cache_store = object()
    rate_limiter = object()
    retry_policy = object()
    maps_client = object()
    matrix_port = object()
    cache_port = object()
    routing_service = object()
    cancel_token = object()
    app = object()
    constructor_calls: dict[str, list[tuple[tuple[object, ...], dict[str, object]]]] = {
        name: []
        for name in (
            "distance",
            "geocode",
            "store",
            "rate",
            "retry",
            "maps",
            "service",
            "token",
            "app",
        )
    }
    logging_levels: list[str] = []

    monkeypatch.setattr(entrypoint, "get_config", lambda: config)
    monkeypatch.setattr(entrypoint, "setup_logging", logging_levels.append)
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.cache.distance_cache"),
        "DistanceCache",
        _factory(distance_cache, constructor_calls["distance"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.cache.geocode_cache"),
        "GeocodeCache",
        _factory(geocode_cache, constructor_calls["geocode"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.cache.store"),
        "CacheStore",
        _factory(cache_store, constructor_calls["store"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.rate_limit"),
        "RateLimiter",
        _factory(rate_limiter, constructor_calls["rate"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.retry"),
        "RetryPolicy",
        _factory(retry_policy, constructor_calls["retry"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.google_maps.client"),
        "GoogleMapsClient",
        _factory(maps_client, constructor_calls["maps"]),
    )
    adapters_module = importlib.import_module("fastest_route.infrastructure.adapters")
    monkeypatch.setattr(
        adapters_module,
        "build_routing_ports",
        lambda **_kwargs: (matrix_port, cache_port),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.core.routing.routing_service"),
        "RoutingService",
        _factory(routing_service, constructor_calls["service"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.shared.cancellation"),
        "CancellationToken",
        _factory(cancel_token, constructor_calls["token"]),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.presentation.gui.app"),
        "RouteApp",
        _factory(app, constructor_calls["app"]),
    )

    result = entrypoint._build_dependencies()

    assert result == (app, maps_client, distance_cache, geocode_cache, cancel_token)
    assert logging_levels == ["INFO"]
    assert constructor_calls["distance"] == [(("distance.json", 60), {})]
    assert constructor_calls["maps"][0][1]["cache"] is distance_cache
    assert constructor_calls["service"][0][1] == {
        "config": config,
        "maps_client": matrix_port,
        "cache_store": cache_port,
    }
    assert constructor_calls["app"][0][1]["routing_service"] is routing_service


def test_build_dependencies_preserves_startup_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        entrypoint,
        "get_config",
        lambda: (_ for _ in ()).throw(ConfigError("tests", "bad config")),
    )

    with pytest.raises(ConfigError, match="fastest_route.entrypoint._build_dependencies"):
        entrypoint._build_dependencies()


def test_build_dependencies_selects_network_free_demo_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SimpleNamespace(
        logging=SimpleNamespace(level="INFO"),
        cache=SimpleNamespace(
            disk_path="distance.json",
            disk_cache_ttl_seconds=60,
            geocode_cache_size=20,
            geocode_disk_path=None,
            geocode_disk_cache_ttl_seconds=120,
            route_cache_size=10,
        ),
    )
    distance_cache = object()
    geocode_cache = object()
    cache_store = object()
    matrix_port = object()
    cache_port = object()
    routing_service = object()
    cancel_token = object()
    app = object()
    app_calls: list[dict[str, object]] = []

    monkeypatch.setattr(entrypoint, "get_config", lambda: config)
    monkeypatch.setattr(entrypoint, "setup_logging", lambda _level: None)
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.cache.distance_cache"),
        "DistanceCache",
        lambda *_args: distance_cache,
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.cache.geocode_cache"),
        "GeocodeCache",
        lambda **_kwargs: geocode_cache,
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.cache.store"),
        "CacheStore",
        lambda **_kwargs: cache_store,
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.google_maps.client").requests,
        "Session",
        lambda: pytest.fail("offline demo constructed a requests.Session"),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.infrastructure.adapters"),
        "build_routing_ports",
        lambda **_kwargs: (matrix_port, cache_port),
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.core.routing.routing_service"),
        "RoutingService",
        lambda **_kwargs: routing_service,
    )
    monkeypatch.setattr(
        importlib.import_module("fastest_route.shared.cancellation"),
        "CancellationToken",
        lambda: cancel_token,
    )

    def build_app(**kwargs: object) -> object:
        app_calls.append(kwargs)
        return app

    monkeypatch.setattr(
        importlib.import_module("fastest_route.presentation.gui.app"),
        "RouteApp",
        build_app,
    )

    result = entrypoint._build_dependencies(demo=True)

    assert result[0] is app
    assert result[1].__class__.__name__ == "DemoMapsClient"
    assert result[2:] == (distance_cache, geocode_cache, cancel_token)
    assert app_calls[0]["offline_demo"] is True


def test_signal_handlers_cancel_and_request_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers: dict[int, Callable[[int, object | None], None]] = {}
    events: list[str] = []
    app = SimpleNamespace(request_shutdown=lambda: events.append("shutdown"))
    token = SimpleNamespace(cancel=lambda: events.append("cancel"))
    monkeypatch.setattr(
        entrypoint.signal,
        "signal",
        lambda signum, handler: handlers.__setitem__(signum, handler),
    )

    entrypoint._install_signal_handlers(app, token)
    handlers[entrypoint.signal.SIGTERM](entrypoint.signal.SIGTERM, None)

    assert set(handlers) == {entrypoint.signal.SIGINT, entrypoint.signal.SIGTERM}
    assert events == ["cancel", "shutdown"]


def test_signal_handler_wraps_shutdown_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers: dict[int, Callable[[int, object | None], None]] = {}
    app = SimpleNamespace(
        request_shutdown=lambda: (_ for _ in ()).throw(ConfigError("tests", "shutdown"))
    )
    token = SimpleNamespace(cancel=lambda: None)
    monkeypatch.setattr(
        entrypoint.signal,
        "signal",
        lambda signum, handler: handlers.__setitem__(signum, handler),
    )
    entrypoint._install_signal_handlers(app, token)

    with pytest.raises(ConfigError, match="Signal handler failed"):
        handlers[entrypoint.signal.SIGINT](entrypoint.signal.SIGINT, None)


def test_signal_setup_wraps_platform_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        entrypoint.signal,
        "signal",
        lambda *_args: (_ for _ in ()).throw(OSError("unsupported")),
    )

    with pytest.raises(AppError, match="Failed to install signal handlers"):
        entrypoint._install_signal_handlers(object(), object())


class _RuntimeResource:
    def __init__(self, method_name: str, events: list[str], *, fail: bool = False) -> None:
        def action() -> None:
            events.append(method_name)
            if fail:
                raise ConfigError("tests", method_name)

        setattr(self, method_name, action)


def test_main_runs_and_cleans_up_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    app = _RuntimeResource("mainloop", events)
    app.shutdown = lambda: events.append("shutdown")
    maps_client = _RuntimeResource("close", events)
    distance_cache = _RuntimeResource("persist", events)
    geocode_cache = _RuntimeResource("persist", events)
    cancel_token = object()
    monkeypatch.setattr(
        entrypoint,
        "_build_dependencies",
        lambda: (app, maps_client, distance_cache, geocode_cache, cancel_token),
    )
    monkeypatch.setattr(
        entrypoint,
        "_install_signal_handlers",
        lambda installed_app, token: events.append(
            "signals" if installed_app is app and token is cancel_token else "wrong"
        ),
    )

    assert entrypoint.main() == 0
    assert events == ["signals", "mainloop", "shutdown", "persist", "persist", "close"]


def test_main_logs_each_cleanup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    app = _RuntimeResource("mainloop", events)
    app.shutdown = _RuntimeResource("shutdown", events, fail=True).shutdown
    maps_client = _RuntimeResource("close", events, fail=True)
    distance_cache = _RuntimeResource("persist", events, fail=True)
    geocode_cache = _RuntimeResource("persist", events, fail=True)
    logger = _CapturedLogger()
    monkeypatch.setattr(
        entrypoint,
        "_build_dependencies",
        lambda: (app, maps_client, distance_cache, geocode_cache, object()),
    )
    monkeypatch.setattr(entrypoint, "_install_signal_handlers", lambda *_args: None)
    monkeypatch.setattr(entrypoint, "logger", logger)

    assert entrypoint.main() == 0
    assert [message for message, _extra in logger.calls] == [
        "App shutdown failed",
        "Cache persist failed",
        "Geocode cache persist failed",
        "Maps client shutdown failed",
    ]


def test_cli_delegates_to_gui_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entrypoint, "main", lambda: 7)
    assert entrypoint.cli([]) == 7


def test_cli_starts_offline_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[bool] = []
    monkeypatch.setattr(entrypoint, "main", lambda *, demo=False: received.append(demo) or 0)

    assert entrypoint.cli(["--demo"]) == 0
    assert received == [True]


def test_cli_loads_local_environment_before_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(entrypoint, "_load_local_environment", lambda: events.append("env"))
    monkeypatch.setattr(entrypoint, "main", lambda: events.append("main") or 0)

    assert entrypoint.cli([]) == 0
    assert events == ["env", "main"]


def test_cli_reports_invalid_environment_file(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _CapturedLogger()
    monkeypatch.setattr(
        entrypoint,
        "_load_local_environment",
        lambda: (_ for _ in ()).throw(ConfigError("tests", "bad env")),
    )
    monkeypatch.setattr(entrypoint, "logger", logger)

    assert entrypoint.cli(["--check-config"]) == 1
    assert logger.calls[0][0] == "Environment load failed"


def test_cli_checks_packaged_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        entrypoint,
        "get_config",
        lambda: SimpleNamespace(environment="test"),
    )

    assert entrypoint.cli(["--check-config"]) == 0
    assert capsys.readouterr().out == "Configuration OK (environment=test)\n"


def test_cli_reports_invalid_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _CapturedLogger()
    monkeypatch.setattr(
        entrypoint,
        "get_config",
        lambda: (_ for _ in ()).throw(ConfigError("tests", "invalid")),
    )
    monkeypatch.setattr(entrypoint, "logger", logger)

    assert entrypoint.cli(["--check-config"]) == 1
    assert logger.calls[0][0] == "Configuration check failed"
    assert logger.calls[0][1]["error_code"] == "E_CONFIG"


def test_python_m_module_exits_with_cli_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entrypoint, "cli", lambda: 9)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("fastest_route.__main__", run_name="__main__")

    assert exc_info.value.code == 9
