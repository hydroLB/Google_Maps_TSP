"""Row construction helpers for the GUI stops input section."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.views.components import (
    create_entry,
    create_field_label,
    create_status_label,
)
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastest_route.presentation.gui.app.views.theme import GuiThemeTokens


@dataclass(frozen=True, slots=True)
class StopRowWidgets:
    """Bundle the widgets that represent one optional stop row."""

    label: ttk.Label
    entry: ttk.Entry
    status: ttk.Label


def build_start_row(
    *,
    frame: ttk.LabelFrame,
    tokens: GuiThemeTokens,
    on_schedule_status_check: Callable[[int], None],
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
) -> tuple[ttk.Entry, ttk.Label]:
    """Build the fixed start-address row and bind validation and autocomplete events."""
    location = "fastest_route.presentation.gui.app.views.sections.input_section_support.rows.build_start_row"
    try:
        create_field_label(root=frame, text="Start (optional):").grid(
            row=0,
            column=0,
            padx=(tokens.control_spacing, tokens.inline_gap),
            pady=(tokens.control_spacing, tokens.row_spacing),
            sticky="e",
        )
        start_entry = create_entry(root=frame, width=tokens.entry_width_key)
        start_entry.grid(
            row=0,
            column=1,
            padx=(0, tokens.control_spacing),
            pady=(tokens.control_spacing, tokens.row_spacing),
            sticky="we",
        )
        start_status = create_status_label(root=frame)
        start_status.grid(row=0, column=2, padx=(tokens.inline_gap, 2), sticky="w")
        _bind_entry_events(
            entry=start_entry,
            status_index=0,
            on_schedule_status_check=on_schedule_status_check,
            on_schedule_autocomplete=on_schedule_autocomplete,
        )
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to build start row.") from exc
    return start_entry, start_status


def build_stop_rows(
    *,
    frame: ttk.LabelFrame,
    tokens: GuiThemeTokens,
    max_stops: int,
    on_update_stop_counter: Callable[[], None],
    on_schedule_status_check: Callable[[int], None],
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
) -> tuple[list[ttk.Entry], list[ttk.Label], list[StopRowWidgets]]:
    """Build all optional stop rows and bind row-specific callbacks."""
    location = "fastest_route.presentation.gui.app.views.sections.input_section_support.rows.build_stop_rows"
    stop_entries: list[ttk.Entry] = []
    status_labels: list[ttk.Label] = []
    stop_rows: list[StopRowWidgets] = []
    try:
        for idx in range(max_stops):
            row_index = idx + 1
            stop_label = create_field_label(root=frame, text=f"Stop {idx + 1}:")
            stop_label.grid(
                row=row_index,
                column=0,
                padx=(tokens.control_spacing, tokens.inline_gap),
                pady=tokens.row_spacing,
                sticky="e",
            )
            entry = create_entry(root=frame, width=tokens.entry_width_standard)
            entry.grid(
                row=row_index,
                column=1,
                padx=(0, tokens.control_spacing),
                pady=tokens.row_spacing,
                sticky="we",
            )
            _bind_entry_events(
                entry=entry,
                status_index=row_index,
                on_schedule_status_check=on_schedule_status_check,
                on_schedule_autocomplete=on_schedule_autocomplete,
                on_key_release_extra=on_update_stop_counter,
            )
            status_label = create_status_label(root=frame)
            status_label.grid(row=row_index, column=2, padx=(tokens.inline_gap, 2), sticky="w")
            stop_entries.append(entry)
            status_labels.append(status_label)
            stop_rows.append(StopRowWidgets(label=stop_label, entry=entry, status=status_label))
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to build stop rows.") from exc
    return stop_entries, status_labels, stop_rows


def build_end_row(
    *,
    frame: ttk.LabelFrame,
    tokens: GuiThemeTokens,
    row_index: int,
    status_index: int,
    on_schedule_status_check: Callable[[int], None],
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
) -> tuple[ttk.Entry, ttk.Label]:
    """Build the fixed end-address row and bind validation and autocomplete events."""
    location = (
        "fastest_route.presentation.gui.app.views.sections.input_section_support.rows.build_end_row"
    )
    try:
        create_field_label(root=frame, text="End (optional):").grid(
            row=row_index,
            column=0,
            padx=(tokens.control_spacing, tokens.inline_gap),
            pady=(tokens.row_spacing, tokens.control_spacing),
            sticky="e",
        )
        end_entry = create_entry(root=frame, width=tokens.entry_width_key)
        end_entry.grid(
            row=row_index,
            column=1,
            padx=(0, tokens.control_spacing),
            pady=(tokens.row_spacing, tokens.control_spacing),
            sticky="we",
        )
        end_status = create_status_label(root=frame)
        end_status.grid(row=row_index, column=2, padx=(tokens.inline_gap, 2), sticky="w")
        _bind_entry_events(
            entry=end_entry,
            status_index=status_index,
            on_schedule_status_check=on_schedule_status_check,
            on_schedule_autocomplete=on_schedule_autocomplete,
        )
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to build end row.") from exc
    return end_entry, end_status


def _bind_entry_events(
    *,
    entry: ttk.Entry,
    status_index: int,
    on_schedule_status_check: Callable[[int], None],
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
    on_key_release_extra: Callable[[], None] | None = None,
) -> None:
    """Bind the standard validation and autocomplete callbacks for an address entry."""
    location = "fastest_route.presentation.gui.app.views.sections.input_section_support.rows._bind_entry_events"
    try:

        def on_focus_out(_event: object) -> None:
            on_schedule_status_check(status_index)

        def on_return(_event: object) -> None:
            on_schedule_status_check(status_index)

        def on_key_release(_event: object) -> None:
            _handle_key_release(
                entry=entry,
                on_schedule_autocomplete=on_schedule_autocomplete,
                on_key_release_extra=on_key_release_extra,
            )

        entry.bind("<FocusOut>", on_focus_out)
        entry.bind("<Return>", on_return)
        entry.bind("<KeyRelease>", on_key_release)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to bind address entry events.") from exc


def _handle_key_release(
    *,
    entry: ttk.Entry,
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
    on_key_release_extra: Callable[[], None] | None,
) -> None:
    """Trigger autocomplete and any extra side effect for an entry key-release event."""
    on_schedule_autocomplete(entry)
    if on_key_release_extra is not None:
        on_key_release_extra()
