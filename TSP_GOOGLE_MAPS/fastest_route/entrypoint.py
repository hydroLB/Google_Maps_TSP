"""Package-native application entry point and dependency wiring."""

from __future__ import annotations

import argparse
import signal
import sys
from typing import TYPE_CHECKING

from fastest_route.config import get_config
from fastest_route.observability.logger import get_logger, setup_logging
from fastest_route.shared.errors import AppError, error_code_for_exception

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.infrastructure.cache.distance_cache import DistanceCache
    from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app import RouteApp
    from fastest_route.shared.cancellation import CancellationToken

logger = get_logger(__name__, component="entrypoint")


def _load_local_environment() -> None:
    """Load the application's stable optional ``.env`` before resolving configuration."""

    from fastest_route.config.dotenv import load_env_file, resolve_env_file_path

    load_env_file(resolve_env_file_path())


def _build_dependencies(
    *, demo: bool = False
) -> tuple[RouteApp, GoogleMapsClient, DistanceCache, GeocodeCache, CancellationToken]:
    """Build infrastructure clients, adapt them to core ports, and assemble the GUI.

    Keeping adapter construction here preserves the core layer's independence from
    concrete Google Maps and cache implementations.
    """
    from fastest_route.core.routing.routing_service import RoutingService
    from fastest_route.infrastructure.adapters import build_routing_ports
    from fastest_route.infrastructure.cache.distance_cache import DistanceCache
    from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache
    from fastest_route.infrastructure.cache.store import CacheStore
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app import RouteApp
    from fastest_route.shared.cancellation import CancellationToken

    location = "fastest_route.entrypoint._build_dependencies"
    try:
        config = get_config()
        setup_logging(config.logging.level)
        distance_cache = DistanceCache(config.cache.disk_path, config.cache.disk_cache_ttl_seconds)
        geocode_cache = GeocodeCache(
            memory_max_items=config.cache.geocode_cache_size,
            disk_path=config.cache.geocode_disk_path,
            disk_ttl_seconds=config.cache.geocode_disk_cache_ttl_seconds,
        )
        cache_store = CacheStore(route_cache_size=config.cache.route_cache_size)
        maps_client: GoogleMapsClient
        if demo:
            from fastest_route.infrastructure.demo.maps_client import DemoMapsClient

            maps_client = DemoMapsClient()
        else:
            from fastest_route.infrastructure.rate_limit import RateLimiter
            from fastest_route.infrastructure.retry import RetryPolicy

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
            maps_client = GoogleMapsClient(
                config=config,
                cache=distance_cache,
                geocode_cache=geocode_cache,
                rate_limiter=rate_limiter,
                retry_policy=retry_policy,
            )
        matrix_port, cache_port = build_routing_ports(
            maps_client=maps_client,
            cache_store=cache_store,
        )
        routing_service = RoutingService(
            config=config,
            maps_client=matrix_port,
            cache_store=cache_port,
        )
        cancel_token = CancellationToken()
        app = RouteApp(
            config=config,
            routing_service=routing_service,
            maps_client=maps_client,
            cache_store=cache_store,
            cancel_token=cancel_token,
            offline_demo=demo,
        )
        return app, maps_client, distance_cache, geocode_cache, cancel_token
    except AppError as exc:
        raise type(exc)(location, str(exc)) from exc


def _install_signal_handlers(app: RouteApp, cancel_token: CancellationToken) -> None:
    """Install OS signal handlers for graceful shutdown.

    Ensures graceful shutdown on SIGINT and SIGTERM."""
    location = "fastest_route.entrypoint._install_signal_handlers"
    try:

        def handle_signal(_signum: int, _frame: object | None) -> None:
            """Handle termination signals by initiating shutdown.

            Ensures graceful shutdown on SIGINT and SIGTERM."""
            try:
                cancel_token.cancel()
                app.request_shutdown()
            except AppError as exc:
                raise type(exc)(location, f"Signal handler failed. {exc}") from exc

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    except (ValueError, OSError) as exc:
        raise AppError(location, "Failed to install signal handlers.") from exc


def main(*, demo: bool = False) -> int:
    """Application entrypoint for the GUI.

    Provides a clean and testable startup path."""
    app: RouteApp | None = None
    maps_client: GoogleMapsClient | None = None
    distance_cache: DistanceCache | None = None
    geocode_cache: GeocodeCache | None = None
    try:
        dependencies = _build_dependencies(demo=True) if demo else _build_dependencies()
        app, maps_client, distance_cache, geocode_cache, cancel_token = dependencies
        _install_signal_handlers(app, cancel_token)
        app.mainloop()
        return 0
    except AppError as exc:
        logger.error(
            "Startup failed",
            extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
        )
        return 1
    finally:
        if app is not None:
            try:
                app.shutdown()
            except AppError as exc:
                logger.error(
                    "App shutdown failed",
                    extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
                )
        if distance_cache is not None:
            try:
                distance_cache.persist()
            except AppError as exc:
                logger.error(
                    "Cache persist failed",
                    extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
                )
        if geocode_cache is not None:
            try:
                geocode_cache.persist()
            except AppError as exc:
                logger.error(
                    "Geocode cache persist failed",
                    extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
                )
        if maps_client is not None:
            try:
                maps_client.close()
            except AppError as exc:
                logger.error(
                    "Maps client shutdown failed",
                    extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
                )


def cli(argv: Sequence[str] | None = None) -> int:
    """Run the packaged command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="fastest-route",
        description="Optimize multi-stop routes with Google Maps.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate the resolved configuration without starting the GUI",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run a deterministic offline demo using bundled NYC landmarks",
    )
    args = parser.parse_args(argv)
    try:
        _load_local_environment()
    except AppError as exc:
        logger.error(
            "Environment load failed",
            extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
        )
        return 1
    if not args.check_config:
        return main(demo=args.demo) if args.demo else main()

    try:
        config = get_config()
    except AppError as exc:
        logger.error(
            "Configuration check failed",
            extra={"error": str(exc), "error_code": error_code_for_exception(exc).value},
        )
        return 1
    print(f"Configuration OK (environment={config.environment})")
    return 0


if __name__ == "__main__":
    sys.exit(cli())
