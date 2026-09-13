"""Widget builder for link action buttons."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.state.widgets import LinkSectionWidgets
from fastest_route.presentation.gui.app.views.components import create_action_button
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable


def build_link_section(
    *,
    root: tk.Misc,
    on_open: Callable[[], None],
    on_copy: Callable[[], None],
    on_export_csv: Callable[[], None],
) -> LinkSectionWidgets:
    """Build link action buttons for opening and copying results."""
    location = "fastest_route.presentation.gui.app.views.sections.link_section.build_link_section"
    if not root:
        raise ValidationError(location, "root is required.")
    try:
        tokens = get_theme_tokens()
        frame_links = ttk.Frame(root, style="App.TFrame")
        frame_links.pack(fill="x", pady=(0, tokens.group_spacing))
        for column in range(3):
            frame_links.columnconfigure(column, weight=1)

        btn_open = create_action_button(
            root=frame_links,
            text="Open in Maps",
            command=on_open,
            state="disabled",
            width=tokens.button_width_secondary,
            is_primary=False,
        )
        btn_open.grid(row=0, column=0, padx=(0, tokens.inline_gap), sticky="ew")
        btn_copy = create_action_button(
            root=frame_links,
            text="Copy link",
            command=on_copy,
            state="disabled",
            width=tokens.button_width_secondary,
            is_primary=False,
        )
        btn_copy.grid(
            row=0,
            column=1,
            padx=(tokens.inline_gap, tokens.inline_gap),
            sticky="ew",
        )
        btn_export = create_action_button(
            root=frame_links,
            text="Export CSV",
            command=on_export_csv,
            state="disabled",
            width=tokens.button_width_secondary,
            is_primary=False,
        )
        btn_export.grid(row=0, column=2, padx=(tokens.inline_gap, 0), sticky="ew")
        return LinkSectionWidgets(btn_open=btn_open, btn_copy=btn_copy, btn_export=btn_export)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to initialize link section.") from exc
