"""Reusable Tkinter widget factory helpers for consistent GUI construction."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.views.theme import get_theme_tokens, resolve_status_style
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable


def create_section_frame(*, root: tk.Misc, title: str) -> ttk.LabelFrame:
    """Create a standardized section container with shared visual styling."""
    location = "fastest_route.presentation.gui.app.views.components.primitives.create_section_frame"
    if not root:
        raise ValidationError(location, "root is required.")
    return ttk.LabelFrame(root, text=title, style="Section.Outer.TLabelframe")


def create_field_label(*, root: tk.Misc, text: str) -> ttk.Label:
    """Create a right-aligned form field label with shared width and typography."""
    location = "fastest_route.presentation.gui.app.views.components.primitives.create_field_label"
    if not root:
        raise ValidationError(location, "root is required.")
    tokens = get_theme_tokens()
    return ttk.Label(
        root,
        text=text,
        width=tokens.field_label_width,
        anchor="e",
        style="FormLabel.TLabel",
    )


def create_entry(*, root: tk.Misc, width: int | None = None) -> ttk.Entry:
    """Create a standardized text entry control used by GUI forms."""
    location = "fastest_route.presentation.gui.app.views.components.primitives.create_entry"
    if not root:
        raise ValidationError(location, "root is required.")
    entry = ttk.Entry(root, style="App.TEntry")
    if width is not None:
        entry.configure(width=width)
    return entry


def create_status_label(*, root: tk.Misc) -> ttk.Label:
    """Create a status label with consistent size and default informational style."""
    location = "fastest_route.presentation.gui.app.views.components.primitives.create_status_label"
    if not root:
        raise ValidationError(location, "root is required.")
    tokens = get_theme_tokens()
    return ttk.Label(
        root,
        text="",
        anchor="w",
        width=tokens.status_label_width,
        style=resolve_status_style(status_text="Ready"),
    )


def create_google_maps_attribution(*, root: tk.Misc) -> ttk.Label:
    """Create the provider attribution shown with Google Maps API content."""
    location = (
        "fastest_route.presentation.gui.app.views.components.primitives."
        "create_google_maps_attribution"
    )
    if not root:
        raise ValidationError(location, "root is required.")
    return ttk.Label(
        root,
        text="Google Maps",
        anchor="e",
        style="GoogleMapsAttribution.TLabel",
    )


def create_action_button(
    *,
    root: tk.Misc,
    text: str,
    command: Callable[[], None],
    is_primary: bool,
    width: int,
    state: str = "normal",
) -> ttk.Button:
    """Create a standardized action button with primary or secondary styling."""
    location = "fastest_route.presentation.gui.app.views.components.primitives.create_action_button"
    if not root:
        raise ValidationError(location, "root is required.")
    style_name = "Primary.TButton" if is_primary else "Secondary.TButton"
    return ttk.Button(
        root,
        text=text,
        command=command,
        width=width,
        state=state,
        style=style_name,
    )
