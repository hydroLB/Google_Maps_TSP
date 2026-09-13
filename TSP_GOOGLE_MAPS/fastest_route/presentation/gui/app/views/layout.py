"""Top-level layout builder for the RouteApp widget tree."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.state.widgets import RouteAppWidgets
from fastest_route.presentation.gui.app.views.sections.action_section import build_action_section
from fastest_route.presentation.gui.app.views.sections.input_section import build_stops_section
from fastest_route.presentation.gui.app.views.sections.link_section import build_link_section
from fastest_route.presentation.gui.app.views.sections.mode_section import build_mode_section
from fastest_route.presentation.gui.app.views.sections.output_section import build_output_section
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastest_route.config.registry import AppConfig


def build_route_app_widgets(
    *,
    root: tk.Tk,
    config: AppConfig,
    on_update_stop_counter: Callable[[], None],
    on_schedule_status_check: Callable[[int], None],
    on_schedule_autocomplete: Callable[[ttk.Entry], None],
    on_set_api_key: Callable[[], None],
    on_guided_entry: Callable[[], None],
    on_optimize: Callable[[], None],
    on_cancel: Callable[[], None],
    on_open: Callable[[], None],
    on_copy: Callable[[], None],
    on_export_csv: Callable[[], None],
) -> RouteAppWidgets:
    """Build the entire widget tree and bind event handlers."""
    location = "fastest_route.presentation.gui.app.views.layout.build_route_app_widgets"
    if not root:
        raise ValidationError(location, "root is required.")
    if not config:
        raise ValidationError(location, "config is required.")
    try:
        tokens = get_theme_tokens()
        page = ttk.Frame(
            root,
            style="Page.TFrame",
            padding=(tokens.window_padding_x, tokens.window_padding_y),
        )
        page.pack(fill="both", expand=True)

        stops = build_stops_section(
            root=page,
            config=config,
            on_update_stop_counter=on_update_stop_counter,
            on_schedule_status_check=on_schedule_status_check,
            on_schedule_autocomplete=on_schedule_autocomplete,
        )
        mode = build_mode_section(root=page, config=config)
        actions = build_action_section(
            root=page,
            on_set_api_key=on_set_api_key,
            on_guided_entry=on_guided_entry,
            on_optimize=on_optimize,
            on_cancel=on_cancel,
        )
        output = build_output_section(root=page)
        links = build_link_section(
            root=page,
            on_open=on_open,
            on_copy=on_copy,
            on_export_csv=on_export_csv,
        )
        return RouteAppWidgets(
            stops=stops,
            mode=mode,
            actions=actions,
            output=output,
            links=links,
        )
    except (tk.TclError, ValidationError) as exc:
        raise ValidationError(location, str(exc)) from exc
