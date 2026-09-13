"""Shutdown flow helpers for the GUI."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from fastest_route.shared.errors import AppError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastest_route.presentation.gui.app.controllers.routing_controller import RoutingController
    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState
    from fastest_route.shared.cancellation import CancellationToken


def request_shutdown(
    *,
    runtime: RouteAppRuntimeState,
    routing_controller: RoutingController,
    app_cancel_token: CancellationToken,
    schedule_destroy: Callable[[], None],
    location: str,
) -> None:
    """Request application shutdown and cancel active work."""
    if runtime.is_shutting_down:
        return
    try:
        runtime.is_shutting_down = True
        routing_controller.cancel()
        app_cancel_token.cancel()
        schedule_destroy()
    except (tk.TclError, AppError) as exc:
        raise ValidationError(location, "Failed to close application.") from exc
