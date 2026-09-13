"""Guided workflow for importing multiple stops from multiline text."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.dialogs.guided_entry_dialog import prompt_guided_entry
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.config.registry import AppConfig


def apply_guided_entry_lines(
    *,
    lines: Sequence[str],
    stop_entries: Sequence[ttk.Entry],
    set_visible_stops: Callable[[int], None],
    update_stop_counter: Callable[[], None],
    clear_status_labels: Callable[[], None],
    schedule_status_check: Callable[[int], None],
) -> None:
    """Expand the stops section before populating every imported line."""
    location = "fastest_route.presentation.gui.app.flows.guided_entry.apply_guided_entry_lines"
    if not lines:
        raise ValidationError(location, "At least one stop is required.")
    if len(lines) > len(stop_entries):
        raise ValidationError(location, "Imported stops exceed the available stop fields.")

    try:
        set_visible_stops(len(lines))
        for entry, value in zip(stop_entries, lines, strict=False):
            entry.delete(0, "end")
            entry.insert(0, value)
        clear_status_labels()
        update_stop_counter()
        for stop_index in range(1, len(lines) + 1):
            schedule_status_check(stop_index)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to populate imported stops.") from exc


def run_guided_entry(
    *,
    root: tk.Tk,
    config: AppConfig,
    stop_entries: Sequence[ttk.Entry],
    set_visible_stops: Callable[[int], None],
    update_stop_counter: Callable[[], None],
    clear_status_labels: Callable[[], None],
    schedule_status_check: Callable[[int], None],
) -> None:
    """Open the stop-import dialog and apply its result to the main form."""
    try:
        lines = prompt_guided_entry(
            root=root,
            min_stops=config.ui.min_stops,
            max_stops=config.ui.max_stops,
        )
        if lines is None:
            return
        apply_guided_entry_lines(
            lines=lines,
            stop_entries=stop_entries,
            set_visible_stops=set_visible_stops,
            update_stop_counter=update_stop_counter,
            clear_status_labels=clear_status_labels,
            schedule_status_check=schedule_status_check,
        )
    except tk.TclError as exc:
        raise ValidationError(
            "fastest_route.presentation.gui.app.flows.guided_entry.run_guided_entry",
            "Guided entry failed.",
        ) from exc
