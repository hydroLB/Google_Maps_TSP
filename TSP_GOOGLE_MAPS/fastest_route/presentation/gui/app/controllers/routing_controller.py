"""Routing workflow orchestration for the GUI, including request building and rendering."""

from __future__ import annotations

import threading
import tkinter as tk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.controllers.routing_job import compute_route_artifacts
from fastest_route.presentation.gui.app.controllers.routing_ui import (
    render_cancelled,
    render_error,
    render_result,
    set_busy,
)
from fastest_route.presentation.gui.app.dialogs.address_selection_dialog import select_address
from fastest_route.presentation.gui.app.workflow.route_request_builder import build_route_request
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import (
    ErrorCode,
    ExternalServiceError,
    ValidationError,
    error_code_for_exception,
    format_boundary_error_message,
)
from fastest_route.shared.utils.address_utils import (
    normalize_address_input,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from fastest_route.config.registry import AppConfig
    from fastest_route.core.routing.routing_service import RoutingService
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState
    from fastest_route.presentation.gui.app.state.widgets import RouteAppWidgets
    from fastest_route.shared.types import RouteRequest, RouteResult


class RoutingController:
    """Manage route request validation, background computation, and UI rendering."""

    def __init__(
        self,
        *,
        root: tk.Tk,
        config: AppConfig,
        routing_service: RoutingService,
        maps_client: GoogleMapsClient,
        runtime: RouteAppRuntimeState,
        widgets: RouteAppWidgets,
        correlation_context: Callable[[], AbstractContextManager[object]],
    ) -> None:
        """Initialize the routing controller."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController.__init__"
        if not root:
            raise ValidationError(location, "root is required.")
        if not config:
            raise ValidationError(location, "config is required.")
        if not routing_service:
            raise ValidationError(location, "routing_service is required.")
        if not maps_client:
            raise ValidationError(location, "maps_client is required.")
        if not runtime:
            raise ValidationError(location, "runtime is required.")
        if not widgets:
            raise ValidationError(location, "widgets is required.")
        self._root = root
        self._config = config
        self._routing_service = routing_service
        self._maps_client = maps_client
        self._runtime = runtime
        self._widgets = widgets
        self._correlation_context_factory = correlation_context

    def start(self) -> None:
        """
        Validate inputs, build a RouteRequest, and start route computation in a background thread.
        """
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController.start"
        token = CancellationToken()
        self._runtime.task_cancel_token = token
        try:
            self._set_busy(True)

            request = build_route_request(
                config=self._config,
                start_raw=self._widgets.stops.start_entry.get(),
                end_raw=self._widgets.stops.end_entry.get(),
                stop_raws=[entry.get() for entry in self._widgets.stops.stop_entries],
                mode_value=self._widgets.mode.mode_var.get(),
                optimize_value=self._widgets.mode.optimize_var.get(),
                trip_value=self._widgets.mode.trip_var.get(),
                geocode=self._geocode_for_request,
                normalize=normalize_address_input,
            )

            thread = threading.Thread(
                target=self._compute_route_worker,
                args=(request, token),
                daemon=True,
            )
            self._runtime.active_thread = thread
            thread.start()
        except ValidationError:
            if self._is_current_job(token):
                self._runtime.task_cancel_token = None
            self._set_busy(False)
            raise
        except tk.TclError as exc:
            if self._is_current_job(token):
                self._runtime.task_cancel_token = None
            self._set_busy(False)
            raise ValidationError(location, "Failed to start routing task.") from exc

    def cancel(self) -> None:
        """Cancel the current routing task if running and reset the busy state."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController.cancel"
        try:
            token = self._runtime.task_cancel_token
            if token is not None:
                token.cancel()
                if self._is_current_job(token):
                    self._runtime.task_cancel_token = None
            self._set_busy(False)
        except (ValidationError, tk.TclError) as exc:
            raise ValidationError(location, str(exc)) from exc

    def _geocode_for_request(self, address: str) -> str:
        """Resolve an address through Google Maps geocoding with user selection on ambiguity."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController._geocode_for_request"
        try:
            return self._maps_client.geocode(
                address, select_callback=lambda opts: select_address(self._root, opts)
            )
        except (ExternalServiceError, ValidationError) as exc:
            raise ValidationError(location, str(exc)) from exc

    def _compute_route_worker(self, request: RouteRequest, token: CancellationToken) -> None:
        """
        Execute routing work in a background thread and schedule UI updates.

        Offloads heavy work from the UI thread while preserving thread-safe rendering.
        """
        with self._correlation_context_factory():
            try:
                route_link, summary, result = compute_route_artifacts(
                    routing_service=self._routing_service,
                    request=request,
                    cancellation_token=token,
                )

                def render_success() -> None:
                    """Execute `render_success`."""
                    if self._is_current_job(token):
                        self._render_result(route_link, summary, request, result)

                self._root.after(0, render_success)
            except Exception as exc:
                code = error_code_for_exception(exc)
                message = format_boundary_error_message(exc)

                def render_mapped_error() -> None:
                    """Render the mapped boundary error in the UI."""
                    if not self._is_current_job(token):
                        return
                    if code == ErrorCode.CANCELLED:
                        self._render_cancelled(message)
                    else:
                        title = self._error_title_for_code(code)
                        self._render_error(title, message)

                self._root.after(0, render_mapped_error)
            finally:

                def finish_job() -> None:
                    """Return the UI to idle only when this is still the active job."""
                    if self._is_current_job(token):
                        self._runtime.task_cancel_token = None
                        self._set_busy(False)

                self._root.after(0, finish_job)

    def _is_current_job(self, token: CancellationToken) -> bool:
        """Return whether ``token`` identifies the active routing job."""
        return self._runtime.task_cancel_token is token

    def _error_title_for_code(self, code: ErrorCode) -> str:
        """Return a consistent UI error title for a normalized error code."""
        if code == ErrorCode.VALIDATION:
            return "Input Error"
        if code == ErrorCode.EXTERNAL_IO:
            return "External Service Error"
        if code == ErrorCode.RATE_LIMIT:
            return "Rate Limit Error"
        if code == ErrorCode.CACHE:
            return "Cache Error"
        if code == ErrorCode.CONFIG:
            return "Configuration Error"
        return "Internal Error"

    def _render_result(
        self, route_link: str, summary: str, request: RouteRequest, result: RouteResult
    ) -> None:
        """Render a completed route result in the UI."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController._render_result"
        render_result(
            widgets=self._widgets,
            runtime=self._runtime,
            route_link=route_link,
            summary=summary,
            request=request,
            result=result,
            location=location,
        )

    def _render_error(self, title: str, message: str) -> None:
        """Render an error message in the UI and dialog."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController._render_error"
        render_error(widgets=self._widgets, title=title, message=message, location=location)

    def _render_cancelled(self, message: str) -> None:
        """Render a cancellation update in the UI."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController._render_cancelled"
        render_cancelled(widgets=self._widgets, message=message, location=location)

    def _set_busy(self, busy: bool) -> None:
        """Update UI controls for busy or idle states."""
        location = "fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController._set_busy"
        set_busy(widgets=self._widgets, runtime=self._runtime, busy=busy, location=location)
