"""Stop counter label update helpers for the GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from fastest_route.shared.errors import ValidationError


def update_stop_counter_label(
    *,
    frame: ttk.LabelFrame,
    stop_entries: list[ttk.Entry],
    min_stops: int,
    max_stops: int,
) -> None:
    """Compute and render the stop counter label based on entry widget state."""
    location = "fastest_route.presentation.gui.app.flows.stop_counter.update_stop_counter_label"
    try:
        shown = len([entry for entry in stop_entries if not entry.instate(["disabled"])])
        filled = len(
            [
                entry
                for entry in stop_entries
                if not entry.instate(["disabled"]) and entry.get().strip()
            ]
        )
        frame.configure(text=f"Stops ({filled}/{shown} filled, min {min_stops}, max {max_stops})")
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to update stop counter label.") from exc
