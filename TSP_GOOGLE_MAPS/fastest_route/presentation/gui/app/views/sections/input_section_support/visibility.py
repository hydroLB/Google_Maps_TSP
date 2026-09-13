"""Visibility management helpers for optional stop rows in the GUI input section."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.views.components import create_action_button
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastest_route.presentation.gui.app.views.sections.input_section_support.rows import (
        StopRowWidgets,
    )
    from fastest_route.presentation.gui.app.views.theme import GuiThemeTokens


def clamp_visible_stop_count(*, min_stops: int, max_stops: int, requested: int) -> int:
    """Clamp a requested visible stop count into a valid [min_stops, max_stops] range."""
    location = "fastest_route.presentation.gui.app.views.sections.input_section_support.visibility.clamp_visible_stop_count"
    if min_stops <= 0:
        raise ValidationError(location, "min_stops must be positive.")
    if max_stops < min_stops:
        raise ValidationError(location, "max_stops must be greater than or equal to min_stops.")
    if requested < min_stops:
        return min_stops
    if requested > max_stops:
        return max_stops
    return requested


@dataclass(slots=True)
class StopVisibilityManager:
    """Manage the visible optional stop count and synchronize row widgets and controls."""

    frame: ttk.LabelFrame
    tokens: GuiThemeTokens
    min_stops: int
    max_stops: int
    stop_rows: list[StopRowWidgets]
    on_update_stop_counter: Callable[[], None]
    visible_stops: int
    shown_label: ttk.Label | None = None
    btn_add: ttk.Button | None = None
    btn_remove: ttk.Button | None = None

    def build_controls(self) -> None:
        """Create the add/remove controls used to change the visible stop count."""
        location = "fastest_route.presentation.gui.app.views.sections.input_section_support.visibility.StopVisibilityManager.build_controls"
        try:
            controls = ttk.Frame(self.frame, style="App.TFrame")
            controls.grid(
                row=self.max_stops + 2,
                column=0,
                columnspan=3,
                pady=(self.tokens.control_spacing, self.tokens.row_spacing),
                sticky="we",
            )
            controls.columnconfigure(0, weight=1)
            self.shown_label = ttk.Label(controls, text="", style="Hint.TLabel")
            self.shown_label.pack(side="left", padx=(0, self.tokens.control_spacing))
            self.btn_add = create_action_button(
                root=controls,
                text="+ Add stop",
                command=lambda: None,
                is_primary=False,
                width=self.tokens.button_width_secondary,
            )
            self.btn_add.pack(side="left", padx=self.tokens.inline_gap)
            self.btn_remove = create_action_button(
                root=controls,
                text="- Remove stop",
                command=lambda: None,
                is_primary=False,
                width=self.tokens.button_width_secondary,
            )
            self.btn_remove.pack(side="left", padx=self.tokens.inline_gap)
            self.btn_add.configure(command=lambda: self.apply_visible_stops(self.visible_stops + 1))
            self.btn_remove.configure(
                command=lambda: self.apply_visible_stops(self.visible_stops - 1)
            )
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to build stop visibility controls.") from exc

    def apply_visible_stops(self, requested: int) -> None:
        """Apply a new visible stop count, clamped to the configured bounds."""
        location = "fastest_route.presentation.gui.app.views.sections.input_section_support.visibility.StopVisibilityManager.apply_visible_stops"
        next_visible = clamp_visible_stop_count(
            min_stops=self.min_stops,
            max_stops=self.max_stops,
            requested=requested,
        )
        try:
            for index, row in enumerate(self.stop_rows):
                self._set_stop_row_visible(row=row, is_visible=index < next_visible)
            self.visible_stops = next_visible
            self._refresh_controls()
            self.on_update_stop_counter()
        except ValidationError:
            raise
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to apply stop visibility.") from exc

    def _set_stop_row_visible(self, *, row: StopRowWidgets, is_visible: bool) -> None:
        """Show a stop row, or disable and hide it so it cannot retain focus."""
        location = "fastest_route.presentation.gui.app.views.sections.input_section_support.visibility.StopVisibilityManager._set_stop_row_visible"
        try:
            if is_visible:
                row.label.grid()
                row.entry.state(["!disabled"])
                row.entry.grid()
                row.status.grid()
                return
            row.entry.delete(0, "end")
            row.status.configure(text="")
            row.entry.state(["disabled"])
            row.label.grid_remove()
            row.entry.grid_remove()
            row.status.grid_remove()
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to update stop row visibility.") from exc

    def _refresh_controls(self) -> None:
        """Refresh the stop-count summary text and add/remove button enabled state."""
        location = "fastest_route.presentation.gui.app.views.sections.input_section_support.visibility.StopVisibilityManager._refresh_controls"
        if self.shown_label is None or self.btn_add is None or self.btn_remove is None:
            raise ValidationError(location, "Visibility controls are not initialized.")
        self.shown_label.configure(text=f"Stops shown: {self.visible_stops}/{self.max_stops}")
        self.btn_remove.configure(
            state="normal" if self.visible_stops > self.min_stops else "disabled"
        )
        self.btn_add.configure(
            state="normal" if self.visible_stops < self.max_stops else "disabled"
        )
