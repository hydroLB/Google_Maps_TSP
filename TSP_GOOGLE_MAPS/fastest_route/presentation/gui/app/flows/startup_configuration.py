"""First-run startup configuration flow for prompting a required Google Maps API key."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.flows.api_key import prompt_and_apply_api_key

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable
    from pathlib import Path

    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient


def ensure_startup_configuration(
    *,
    root: tk.Tk,
    maps_client: GoogleMapsClient,
    env_path: Path,
    persist_env_var: Callable[[Path, str, str], None],
) -> None:
    """Prompt for an API key before the user interacts with the GUI when credentials are missing."""
    if maps_client.has_api_key():
        return

    prompt_and_apply_api_key(
        root=root,
        maps_client=maps_client,
        env_path=env_path,
        persist_env_var=persist_env_var,
    )
