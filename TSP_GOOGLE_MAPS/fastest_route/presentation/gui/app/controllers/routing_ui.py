"""UI update helpers for the routing workflow."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.flows.errors import strip_location_prefix
from fastest_route.presentation.gui.app.views.theme import resolve_status_style
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState
    from fastest_route.presentation.gui.app.state.widgets import RouteAppWidgets
    from fastest_route.shared.types import RouteRequest, RouteResult


def _set_output_view(
    *, widgets: RouteAppWidgets, text: str, status_text: str, status_style: str | None = None
) -> None:
    """Apply output panel text and status label updates in one place."""
    widgets.output.text.configure(state="normal")
    widgets.output.text.delete("1.0", "end")
    widgets.output.text.insert("end", text)
    widgets.output.text.configure(state="disabled")
    style_name = (
        status_style if status_style is not None else resolve_status_style(status_text=status_text)
    )
    widgets.output.status_label.configure(text=status_text, style=style_name)


def render_result(
    *,
    widgets: RouteAppWidgets,
    runtime: RouteAppRuntimeState,
    route_link: str,
    summary: str,
    request: RouteRequest,
    result: RouteResult,
    location: str,
) -> None:
    """Render a completed route result in the UI."""
    try:
        clean_summary = strip_location_prefix(summary)
        runtime.route_link = route_link
        runtime.last_request = request
        runtime.last_result = result
        _set_output_view(
            widgets=widgets,
            text=clean_summary,
            status_text="Success",
        )
        widgets.links.btn_open.configure(state="normal")
        widgets.links.btn_copy.configure(state="normal")
        widgets.links.btn_export.configure(state="normal")
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to render result.") from exc


def render_error(*, widgets: RouteAppWidgets, title: str, message: str, location: str) -> None:
    """Render an error message in the UI and display a dialog."""
    try:
        clean_message = strip_location_prefix(message)
        _set_output_view(
            widgets=widgets,
            text=f"Route optimization failed.\n\n{clean_message}",
            status_text="Error",
        )
        messagebox.showerror(title, clean_message)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to render error message.") from exc


def render_cancelled(*, widgets: RouteAppWidgets, message: str, location: str) -> None:
    """Render a cancellation message in the output panel."""
    try:
        clean_message = strip_location_prefix(message)
        _set_output_view(
            widgets=widgets,
            text=clean_message,
            status_text="Ready",
        )
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to render cancellation message.") from exc


def set_busy(
    *,
    widgets: RouteAppWidgets,
    runtime: RouteAppRuntimeState,
    busy: bool,
    location: str,
) -> None:
    """Update UI controls for busy or idle states."""
    try:
        state = "disabled" if busy else "normal"
        widgets.actions.btn_optimize.configure(state=state)
        widgets.actions.btn_guided.configure(state=state)
        widgets.actions.btn_api_key.configure(state=state)
        widgets.actions.btn_cancel.configure(state="normal" if busy else "disabled")
        if busy:
            runtime.route_link = None
            runtime.last_request = None
            runtime.last_result = None
            _set_output_view(
                widgets=widgets,
                text=(
                    "Calculating optimized route.\n\n"
                    "Keep this window open while route data is being collected."
                ),
                status_text="Working",
            )
            widgets.links.btn_open.configure(state="disabled")
            widgets.links.btn_copy.configure(state="disabled")
            widgets.links.btn_export.configure(state="disabled")
        else:
            if (
                runtime.route_link is None
                and str(widgets.output.status_label.cget("text")).strip().lower() == "working"
            ):
                _set_output_view(
                    widgets=widgets,
                    text=(
                        "No route has been generated yet.\n\n"
                        "Add your stops and click Optimize Route."
                    ),
                    status_text="Ready",
                )
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to update busy state.") from exc
