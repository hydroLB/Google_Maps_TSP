"""Tkinter window orchestrator for the route optimization GUI."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from fastest_route.observability.context import correlation_context
from fastest_route.presentation.gui.app.controllers.address_status_controller import (
    AddressStatusController,
)
from fastest_route.presentation.gui.app.controllers.autocomplete_controller import (
    AutocompleteController,
)
from fastest_route.presentation.gui.app.controllers.routing_controller import RoutingController
from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState
from fastest_route.presentation.gui.app.window_support import (
    RouteAppAppearanceMixin,
    RouteAppCommandMixin,
    RouteAppLifecycleMixin,
    RouteAppSetupMixin,
)
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from fastest_route.config.registry import AppConfig
    from fastest_route.core.routing.routing_service import RoutingService
    from fastest_route.infrastructure.cache.store import CacheStore
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app.state.widgets import RouteAppWidgets
    from fastest_route.shared.cancellation import CancellationToken


class RouteApp(
    RouteAppAppearanceMixin,
    RouteAppSetupMixin,
    RouteAppCommandMixin,
    RouteAppLifecycleMixin,
):
    """Render the GUI for route optimization and user interaction."""

    def __init__(
        self,
        *,
        config: AppConfig,
        routing_service: RoutingService,
        maps_client: GoogleMapsClient,
        cache_store: CacheStore,
        cancel_token: CancellationToken,
        offline_demo: bool = False,
    ) -> None:
        """Initialize the GUI application and its dependencies."""
        location = "fastest_route.presentation.gui.app.window.RouteApp.__init__"
        try:
            _validate_route_app_dependencies(
                location=location,
                config=config,
                routing_service=routing_service,
                maps_client=maps_client,
                cache_store=cache_store,
                cancel_token=cancel_token,
            )

            super().__init__()
            self.withdraw()

            self._config = config
            self._routing_service = routing_service
            self._maps_client = maps_client
            self._cache_store = cache_store
            self._app_cancel_token = cancel_token
            self._offline_demo = offline_demo

            self._runtime = RouteAppRuntimeState()
            self._widgets = self._build_ui()
            if self._offline_demo:
                self.title("Fastest Route Optimizer — Offline Demo")
                _prefill_offline_demo(self._widgets)
            self._update_stop_counter()
            self._is_compact_density: bool | None = None
            self._start_responsive_density_follow()
            self._start_os_theme_follow()

            self._autocomplete_controller = AutocompleteController(
                root=self,
                config=self._config,
                maps_client=self._maps_client,
                runtime=self._runtime,
                start_entry=self._widgets.stops.start_entry,
                stop_entries=self._widgets.stops.stop_entries,
                end_entry=self._widgets.stops.end_entry,
                schedule_status_check=self._schedule_status_check,
            )
            self._status_controller = AddressStatusController(
                root=self,
                config=self._config,
                maps_client=self._maps_client,
                runtime=self._runtime,
                start_entry=self._widgets.stops.start_entry,
                stop_entries=self._widgets.stops.stop_entries,
                end_entry=self._widgets.stops.end_entry,
                status_labels=self._widgets.stops.status_labels,
            )
            self._routing_controller = RoutingController(
                root=self,
                config=self._config,
                routing_service=self._routing_service,
                maps_client=self._maps_client,
                runtime=self._runtime,
                widgets=self._widgets,
                correlation_context=correlation_context,
            )

            self.protocol("WM_DELETE_WINDOW", self.request_shutdown)
            self._bind_shortcuts()
            self._ensure_startup_configuration()
            if not self._runtime.is_shutting_down:
                self.deiconify()
                self.after(0, self._show_window)
        except ValidationError:
            raise
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to initialize GUI.") from exc


def _prefill_offline_demo(widgets: RouteAppWidgets) -> None:
    """Show three route stops and populate all demo route fields."""

    from fastest_route.infrastructure.demo.maps_client import DEMO_PREFILL_ADDRESSES

    location = "fastest_route.presentation.gui.app.window._prefill_offline_demo"
    start, *stops, end = DEMO_PREFILL_ADDRESSES
    if len(widgets.stops.stop_entries) < len(stops):
        raise ValidationError(location, "Offline demo requires at least three stop fields.")
    widgets.stops.set_visible_stops(len(stops))
    entries = [
        widgets.stops.start_entry,
        *widgets.stops.stop_entries[: len(stops)],
        widgets.stops.end_entry,
    ]
    for entry, value in zip(entries, (start, *stops, end), strict=True):
        entry.delete(0, tk.END)
        entry.insert(0, value)


def _validate_route_app_dependencies(
    *,
    location: str,
    config: object,
    routing_service: object,
    maps_client: object,
    cache_store: object,
    cancel_token: object,
) -> None:
    """Validate the RouteApp constructor dependencies before Tk initialization begins."""
    if not config:
        raise ValidationError(location, "config is required.")
    if not routing_service:
        raise ValidationError(location, "routing_service is required.")
    if not maps_client:
        raise ValidationError(location, "maps_client is required.")
    if not cache_store:
        raise ValidationError(location, "cache_store is required.")
    if not cancel_token:
        raise ValidationError(location, "cancel_token is required.")
