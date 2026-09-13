"""Widget builder for travel mode and optimization selection controls."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.state.widgets import ModeSectionWidgets
from fastest_route.presentation.gui.app.views.components import (
    create_field_label,
    create_section_frame,
)
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import OptimizeFor, RouteKind, TravelMode

if TYPE_CHECKING:
    from fastest_route.config.registry import AppConfig


def build_mode_section(*, root: tk.Misc, config: AppConfig) -> ModeSectionWidgets:
    """Build travel mode and optimization controls."""
    location = "fastest_route.presentation.gui.app.views.sections.mode_section.build_mode_section"
    if not root:
        raise ValidationError(location, "root is required.")
    if not config:
        raise ValidationError(location, "config is required.")
    try:
        tokens = get_theme_tokens()
        container = create_section_frame(root=root, title="Routing options")
        container.pack(fill="x", pady=(0, tokens.group_spacing))

        frame_mode = ttk.Frame(container, style="App.TFrame")
        frame_mode.pack(fill="x", pady=(0, tokens.row_spacing))
        create_field_label(root=frame_mode, text="Travel mode:").pack(
            side="left", padx=(0, tokens.control_spacing)
        )

        mode_var = tk.StringVar(value=config.routing.default_mode.value)
        for mode in TravelMode:
            ttk.Radiobutton(
                frame_mode,
                text=mode.value.title(),
                variable=mode_var,
                value=mode.value,
                style="App.TRadiobutton",
            ).pack(side="left", padx=(0, tokens.inline_gap))

        frame_optimize = ttk.Frame(container, style="App.TFrame")
        frame_optimize.pack(fill="x", pady=(0, tokens.row_spacing))
        create_field_label(root=frame_optimize, text="Optimize for:").pack(
            side="left", padx=(0, tokens.control_spacing)
        )
        optimize_var = tk.StringVar(value=config.routing.default_optimize_for.value)
        for metric in OptimizeFor:
            ttk.Radiobutton(
                frame_optimize,
                text=metric.value.title(),
                variable=optimize_var,
                value=metric.value,
                style="App.TRadiobutton",
            ).pack(side="left", padx=(0, tokens.inline_gap))

        frame_trip = ttk.Frame(container, style="App.TFrame")
        frame_trip.pack(fill="x")
        create_field_label(root=frame_trip, text="Trip type:").pack(
            side="left", padx=(0, tokens.control_spacing)
        )
        trip_var = tk.StringVar(value=RouteKind.PATH.value)
        ttk.Radiobutton(
            frame_trip,
            text="One-way",
            variable=trip_var,
            value=RouteKind.PATH.value,
            style="Segmented.TRadiobutton",
        ).pack(side="left", padx=(0, tokens.inline_gap))
        ttk.Radiobutton(
            frame_trip,
            text="Round trip",
            variable=trip_var,
            value=RouteKind.ROUND_TRIP.value,
            style="Segmented.TRadiobutton",
        ).pack(side="left", padx=(0, tokens.inline_gap))

        return ModeSectionWidgets(mode_var=mode_var, optimize_var=optimize_var, trip_var=trip_var)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to initialize mode section.") from exc
