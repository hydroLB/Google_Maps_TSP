"""Route link actions for the GUI."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable


def open_route_link(route_link: str | None) -> None:
    """Open the route link in the default web browser."""
    location = "fastest_route.presentation.gui.app.flows.link_actions.open_route_link"
    if not route_link:
        return
    try:
        webbrowser.open(route_link)
    except webbrowser.Error as exc:
        raise ValidationError(location, "Failed to open browser.") from exc


def copy_route_link(
    route_link: str | None,
    *,
    clipboard_clear: Callable[[], None],
    clipboard_append: Callable[[str], None],
    parent: tk.Tk | None = None,
) -> None:
    """Copy the route link to the clipboard and notify the user."""
    location = "fastest_route.presentation.gui.app.flows.link_actions.copy_route_link"
    if not route_link:
        return
    try:
        clipboard_clear()
        clipboard_append(route_link)
        messagebox.showinfo("Copied", "Route link copied to clipboard.", parent=parent)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to copy link to clipboard.") from exc
