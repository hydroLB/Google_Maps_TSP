"""RouteApp shutdown and lifecycle cleanup behavior."""

from __future__ import annotations

import tkinter as tk

from fastest_route.presentation.gui.app.flows.shutdown import (
    request_shutdown as request_shutdown_flow,
)
from fastest_route.presentation.gui.app.window_support.base import RouteAppHost
from fastest_route.shared.errors import AppError, ValidationError


class RouteAppLifecycleMixin(RouteAppHost):
    """Provide RouteApp methods for deterministic shutdown and cleanup."""

    def request_shutdown(self) -> None:
        """Request application shutdown and cancel active work."""
        location = "fastest_route.presentation.gui.app.window_support.lifecycle.RouteAppLifecycleMixin.request_shutdown"
        try:
            request_shutdown_flow(
                runtime=self._runtime,
                routing_controller=self._routing_controller,
                app_cancel_token=self._app_cancel_token,
                schedule_destroy=self._schedule_destroy,
                location=location,
            )
        except ValidationError:
            raise
        except (tk.TclError, AppError) as exc:
            raise ValidationError(location, "Failed to close application.") from exc

    def _schedule_destroy(self) -> None:
        """Schedule destruction of the Tk root on the event loop."""
        self.after(0, self.destroy)

    def shutdown(self) -> None:
        """Perform application cleanup after the Tk main loop exits."""
        location = "fastest_route.presentation.gui.app.window_support.lifecycle.RouteAppLifecycleMixin.shutdown"
        try:
            if not self._runtime.is_shutting_down:
                self.request_shutdown()
        except ValidationError as exc:
            raise ValidationError(location, str(exc)) from exc
