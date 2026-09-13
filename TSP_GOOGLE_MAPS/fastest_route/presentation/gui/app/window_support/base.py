"""Typed host contract for RouteApp mixins."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tkinter import ttk

    from fastest_route.config.registry import AppConfig
    from fastest_route.core.routing.routing_service import RoutingService
    from fastest_route.infrastructure.cache.store import CacheStore
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app.controllers.address_status_controller import (
        AddressStatusController,
    )
    from fastest_route.presentation.gui.app.controllers.autocomplete_controller import (
        AutocompleteController,
    )
    from fastest_route.presentation.gui.app.controllers.routing_controller import (
        RoutingController,
    )
    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState
    from fastest_route.presentation.gui.app.state.widgets import RouteAppWidgets
    from fastest_route.presentation.gui.app.views.theme import GuiAppearance
    from fastest_route.shared.cancellation import CancellationToken


class RouteAppHost(tk.Tk):
    """Describe the attributes and Tk methods expected by RouteApp mixins."""

    _config: AppConfig
    _routing_service: RoutingService
    _maps_client: GoogleMapsClient
    _cache_store: CacheStore
    _app_cancel_token: CancellationToken
    _runtime: RouteAppRuntimeState
    _widgets: RouteAppWidgets
    _autocomplete_controller: AutocompleteController
    _status_controller: AddressStatusController
    _routing_controller: RoutingController
    _is_compact_density: bool | None
    _applied_appearance: GuiAppearance
    _os_theme_poll_ms: int

    def _update_stop_counter(self) -> None:
        """Declare the stop-counter helper used across RouteApp mixins."""
        raise NotImplementedError

    def _schedule_status_check(self, idx: int) -> None:
        """Declare the status-check scheduler used across RouteApp mixins."""
        raise NotImplementedError

    def _schedule_autocomplete(self, entry: ttk.Entry) -> None:
        """Declare the autocomplete scheduler used across RouteApp mixins."""
        raise NotImplementedError

    def on_set_api_key(self) -> None:
        """Declare the API-key command used across RouteApp mixins."""
        raise NotImplementedError

    def guided_entry(self) -> None:
        """Declare the guided-entry command used across RouteApp mixins."""
        raise NotImplementedError

    def on_optimize(self) -> None:
        """Declare the optimize command used across RouteApp mixins."""
        raise NotImplementedError

    def on_cancel(self) -> None:
        """Declare the cancel command used across RouteApp mixins."""
        raise NotImplementedError

    def on_open(self) -> None:
        """Declare the open-link command used across RouteApp mixins."""
        raise NotImplementedError

    def on_copy(self) -> None:
        """Declare the copy-link command used across RouteApp mixins."""
        raise NotImplementedError

    def on_export_csv(self) -> None:
        """Declare the CSV export command used across RouteApp mixins."""
        raise NotImplementedError
