"""Widget builder for the action button row."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.state.widgets import ActionSectionWidgets
from fastest_route.presentation.gui.app.views.components import create_action_button
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable


def build_action_section(
    *,
    root: tk.Misc,
    on_set_api_key: Callable[[], None],
    on_guided_entry: Callable[[], None],
    on_optimize: Callable[[], None],
    on_cancel: Callable[[], None],
) -> ActionSectionWidgets:
    """Build action buttons for guided entry and optimization."""
    location = (
        "fastest_route.presentation.gui.app.views.sections.action_section.build_action_section"
    )
    if not root:
        raise ValidationError(location, "root is required.")
    try:
        tokens = get_theme_tokens()
        frame_btn = ttk.Frame(root, style="App.TFrame")
        frame_btn.pack(fill="x", pady=(0, tokens.group_spacing))
        for column in range(4):
            frame_btn.columnconfigure(column, weight=1)

        btn_api_key = create_action_button(
            root=frame_btn,
            text="Add API Key",
            command=on_set_api_key,
            width=tokens.button_width_secondary,
            is_primary=False,
        )
        btn_api_key.grid(row=0, column=0, padx=(0, tokens.inline_gap), sticky="ew")
        btn_guided = create_action_button(
            root=frame_btn,
            text="Guided Entry",
            command=on_guided_entry,
            width=tokens.button_width_primary,
            is_primary=False,
        )
        btn_guided.grid(
            row=0,
            column=1,
            padx=(tokens.inline_gap, tokens.inline_gap),
            sticky="ew",
        )
        btn_optimize = create_action_button(
            root=frame_btn,
            text="Optimize Route",
            command=on_optimize,
            width=tokens.button_width_primary,
            is_primary=True,
        )
        btn_optimize.grid(
            row=0,
            column=2,
            padx=(tokens.inline_gap, tokens.inline_gap),
            sticky="ew",
        )
        btn_cancel = create_action_button(
            root=frame_btn,
            text="Cancel",
            command=on_cancel,
            width=tokens.button_width_secondary,
            is_primary=False,
        )
        btn_cancel.grid(row=0, column=3, padx=(tokens.inline_gap, 0), sticky="ew")
        btn_cancel.configure(state="disabled")
        return ActionSectionWidgets(
            btn_api_key=btn_api_key,
            btn_guided=btn_guided,
            btn_optimize=btn_optimize,
            btn_cancel=btn_cancel,
        )
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to initialize action section.") from exc
