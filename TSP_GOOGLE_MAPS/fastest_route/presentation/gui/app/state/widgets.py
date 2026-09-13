"""Typed references to Tkinter widgets created for the route application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable
    from tkinter import ttk


@dataclass(frozen=True, slots=True)
class StopsSectionWidgets:
    """Widgets for start and stop inputs and their status indicators."""

    frame: ttk.LabelFrame
    start_entry: ttk.Entry
    stop_entries: list[ttk.Entry]
    status_labels: list[ttk.Label]
    end_entry: ttk.Entry
    set_visible_stops: Callable[[int], None]


@dataclass(frozen=True, slots=True)
class ModeSectionWidgets:
    """Widgets for travel mode and optimization selection."""

    mode_var: tk.StringVar
    optimize_var: tk.StringVar
    trip_var: tk.StringVar


@dataclass(frozen=True, slots=True)
class ActionSectionWidgets:
    """Widgets for user actions such as guided entry, optimize, and cancel."""

    btn_api_key: ttk.Button
    btn_guided: ttk.Button
    btn_optimize: ttk.Button
    btn_cancel: ttk.Button


@dataclass(frozen=True, slots=True)
class OutputSectionWidgets:
    """Widgets for rendering the optimized route output."""

    text: tk.Text
    status_label: ttk.Label


@dataclass(frozen=True, slots=True)
class LinkSectionWidgets:
    """Widgets for link actions such as open in browser and copy to clipboard."""

    btn_open: ttk.Button
    btn_copy: ttk.Button
    btn_export: ttk.Button


@dataclass(frozen=True, slots=True)
class RouteAppWidgets:
    """Bundle all widgets needed by controllers and window orchestration."""

    stops: StopsSectionWidgets
    mode: ModeSectionWidgets
    actions: ActionSectionWidgets
    output: OutputSectionWidgets
    links: LinkSectionWidgets
