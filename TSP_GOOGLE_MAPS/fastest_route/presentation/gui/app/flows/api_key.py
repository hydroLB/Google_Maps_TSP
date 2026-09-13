"""API key prompt and persistence flow for the GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.dialogs.api_key_dialog import prompt_google_maps_api_key
from fastest_route.presentation.gui.app.flows.errors import strip_location_prefix
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient


def prompt_and_apply_api_key(
    *,
    root: tk.Tk,
    maps_client: GoogleMapsClient,
    env_path: Path,
    persist_env_var: Callable[[Path, str, str], None],
) -> None:
    """Prompt the user for a Google Maps API key and apply it for this session."""
    try:
        result = prompt_google_maps_api_key(root=root)
        if result is None:
            return
        key, persist = result
        maps_client.set_api_key(key)

        if persist:
            try:
                persist_env_var(env_path, "GOOGLE_MAPS_API_KEY", key)
            except OSError as exc:
                messagebox.showerror(
                    "Save API key",
                    f"Failed to write .env. {strip_location_prefix(str(exc))}",
                    parent=root,
                )
    except ValidationError as exc:
        messagebox.showerror("Set API Key", strip_location_prefix(str(exc)), parent=root)
    except tk.TclError:
        messagebox.showerror("Set API Key", "Failed to prompt for API key.", parent=root)
