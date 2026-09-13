"""Widget builder for the stops input section (start, optional stops, and end) with status indicators."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.state.widgets import StopsSectionWidgets
from fastest_route.presentation.gui.app.views.components import create_section_frame
from fastest_route.presentation.gui.app.views.sections.input_section_support import (
    StopVisibilityManager,
    build_end_row,
    build_start_row,
    build_stop_rows,
    clamp_visible_stop_count,
)
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastest_route.config.registry import AppConfig


def build_stops_section(
    *,
    root: tk.Misc,
    config: AppConfig,
    on_update_stop_counter: Callable[[], None],
    on_schedule_status_check: Callable[[int], None],
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
) -> StopsSectionWidgets:
    """Build the address input section for start, stop, and end entries."""
    location = "fastest_route.presentation.gui.app.views.sections.input_section.build_stops_section"
    if not root:
        raise ValidationError(location, "root is required.")
    if not config:
        raise ValidationError(location, "config is required.")
    try:
        tokens = get_theme_tokens()
        frame = create_section_frame(root=root, title="Stops")
        frame.pack(fill="x", expand=False, pady=(0, tokens.group_spacing))

        start_entry, start_status = build_start_row(
            frame=frame,
            tokens=tokens,
            on_schedule_status_check=on_schedule_status_check,
            on_schedule_autocomplete=on_schedule_autocomplete,
        )
        stop_entries, stop_statuses, stop_rows = build_stop_rows(
            frame=frame,
            tokens=tokens,
            max_stops=config.ui.max_stops,
            on_update_stop_counter=on_update_stop_counter,
            on_schedule_status_check=on_schedule_status_check,
            on_schedule_autocomplete=on_schedule_autocomplete,
        )
        end_row_index = config.ui.max_stops + 1
        end_entry, end_status = build_end_row(
            frame=frame,
            tokens=tokens,
            row_index=end_row_index,
            status_index=end_row_index,
            on_schedule_status_check=on_schedule_status_check,
            on_schedule_autocomplete=on_schedule_autocomplete,
        )
        frame.columnconfigure(1, weight=1)

        visible_stops = clamp_visible_stop_count(
            min_stops=config.ui.min_stops,
            max_stops=config.ui.max_stops,
            requested=config.ui.min_stops,
        )
        visibility_manager = StopVisibilityManager(
            frame=frame,
            tokens=tokens,
            min_stops=config.ui.min_stops,
            max_stops=config.ui.max_stops,
            stop_rows=stop_rows,
            on_update_stop_counter=on_update_stop_counter,
            visible_stops=visible_stops,
        )
        visibility_manager.build_controls()
        visibility_manager.apply_visible_stops(visible_stops)

        root.after(0, on_update_stop_counter)
        return StopsSectionWidgets(
            frame=frame,
            start_entry=start_entry,
            stop_entries=stop_entries,
            status_labels=[start_status, *stop_statuses, end_status],
            end_entry=end_entry,
            set_visible_stops=visibility_manager.apply_visible_stops,
        )
    except (tk.TclError, ValidationError) as exc:
        raise ValidationError(location, str(exc)) from exc


__all__ = ["build_stops_section", "clamp_visible_stop_count"]
