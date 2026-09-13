"""RouteApp setup helpers for widget construction and startup configuration."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from fastest_route.config.dotenv import resolve_env_file_path
from fastest_route.infrastructure.envfile import upsert_env_var
from fastest_route.presentation.gui.app.flows.startup_configuration import (
    ensure_startup_configuration,
)
from fastest_route.presentation.gui.app.views.layout import build_route_app_widgets
from fastest_route.presentation.gui.app.views.theme import (
    apply_theme_from_preference,
    get_theme_tokens,
)
from fastest_route.presentation.gui.app.window_support.base import RouteAppHost
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from fastest_route.presentation.gui.app.state.widgets import RouteAppWidgets


class RouteAppSetupMixin(RouteAppHost):
    """Provide RouteApp setup methods for widget creation and startup configuration."""

    def _build_ui(self) -> RouteAppWidgets:
        """Build and wire all widgets for the application window."""
        location = (
            "fastest_route.presentation.gui.app.window_support.setup.RouteAppSetupMixin._build_ui"
        )
        try:
            tokens = get_theme_tokens()
            self.title("Fastest Route Optimizer")
            self.geometry(f"{tokens.window_width}x{tokens.window_height}")
            self.minsize(tokens.window_min_width, tokens.window_min_height)
            self._applied_appearance = apply_theme_from_preference(
                root=self, preference=self._config.ui.theme_mode
            )
            return build_route_app_widgets(
                root=self,
                config=self._config,
                on_update_stop_counter=self._update_stop_counter,
                on_schedule_status_check=self._schedule_status_check,
                on_schedule_autocomplete=self._schedule_autocomplete,
                on_set_api_key=self.on_set_api_key,
                on_guided_entry=self.guided_entry,
                on_optimize=self.on_optimize,
                on_cancel=self.on_cancel,
                on_open=self.on_open,
                on_copy=self.on_copy,
                on_export_csv=self.on_export_csv,
            )
        except (tk.TclError, ValidationError) as exc:
            raise ValidationError(location, str(exc)) from exc

    def _ensure_startup_configuration(self) -> None:
        """Prompt for an API key before the user interacts with the GUI when credentials are missing."""
        ensure_startup_configuration(
            root=self,
            maps_client=self._maps_client,
            env_path=resolve_env_file_path(),
            persist_env_var=upsert_env_var,
        )
