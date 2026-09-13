"""Optimize action flow for the GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.flows.errors import strip_location_prefix
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient


def handle_optimize_action(
    *,
    root: tk.Tk,
    maps_client: GoogleMapsClient,
    prompt_api_key: Callable[[], None],
    start_routing: Callable[[], None],
) -> None:
    """Validate prerequisites for optimization and start the routing workflow."""
    try:
        if not maps_client.has_api_key():
            prompt_api_key()
            if not maps_client.has_api_key():
                messagebox.showerror(
                    "API key required",
                    "Set a Google Maps API key to optimize routes.",
                    parent=root,
                )
                return
        start_routing()
    except ValidationError as exc:
        messagebox.showerror("Input error", strip_location_prefix(str(exc)), parent=root)
