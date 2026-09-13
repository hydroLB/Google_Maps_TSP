"""RouteApp command handlers for shortcuts, routing actions, and UI scheduling."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from fastest_route.config.dotenv import resolve_env_file_path
from fastest_route.infrastructure.envfile import upsert_env_var
from fastest_route.presentation.gui.app.flows.api_key import prompt_and_apply_api_key
from fastest_route.presentation.gui.app.flows.guided_entry import run_guided_entry
from fastest_route.presentation.gui.app.flows.link_actions import copy_route_link, open_route_link
from fastest_route.presentation.gui.app.flows.optimize_action import handle_optimize_action
from fastest_route.presentation.gui.app.flows.route_csv_export import export_route_csv
from fastest_route.presentation.gui.app.flows.stop_counter import update_stop_counter_label
from fastest_route.presentation.gui.app.window_support.base import RouteAppHost
from fastest_route.shared.errors import AppError, ValidationError


class RouteAppCommandMixin(RouteAppHost):
    """Provide RouteApp methods for keyboard shortcuts, command handlers, and UI scheduling."""

    def _bind_shortcuts(self) -> None:
        """Register cross-platform keyboard shortcuts for optimize and cancel actions."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin._bind_shortcuts"
        try:
            self.bind("<Control-Return>", self._on_optimize_shortcut)
            self.bind("<Command-Return>", self._on_optimize_shortcut)
            self.bind("<Escape>", self._on_cancel_shortcut)
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to bind keyboard shortcuts.") from exc

    def _on_optimize_shortcut(self, _event: object) -> str:
        """Handle optimize keyboard shortcut requests."""
        if self._widgets.actions.btn_optimize.instate(["disabled"]):
            return "break"
        self.on_optimize()
        return "break"

    def _on_cancel_shortcut(self, _event: object) -> str:
        """Handle cancel keyboard shortcut requests."""
        if self._widgets.actions.btn_cancel.instate(["disabled"]):
            return "break"
        self.on_cancel()
        return "break"

    def _update_stop_counter(self) -> None:
        """Update the stop counter label based on current inputs."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin._update_stop_counter"
        widgets = getattr(self, "_widgets", None)
        if widgets is None:
            return
        try:
            update_stop_counter_label(
                frame=widgets.stops.frame,
                stop_entries=widgets.stops.stop_entries,
                min_stops=self._config.ui.min_stops,
                max_stops=self._config.ui.max_stops,
            )
        except ValidationError as exc:
            raise ValidationError(location, str(exc)) from exc

    def _schedule_status_check(self, idx: int) -> None:
        """Debounce and schedule a background address validation status update."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin._schedule_status_check"
        try:
            self._status_controller.schedule(idx)
        except AppError as exc:
            raise ValidationError(location, str(exc)) from exc

    def _schedule_autocomplete(self, entry: ttk.Entry) -> None:
        """Debounce and schedule autocomplete for an entry widget."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin._schedule_autocomplete"
        try:
            self._autocomplete_controller.schedule(entry)
        except AppError as exc:
            raise ValidationError(location, str(exc)) from exc

    def on_optimize(self) -> None:
        """Handle the optimize route action."""
        handle_optimize_action(
            root=self,
            maps_client=self._maps_client,
            prompt_api_key=self.on_set_api_key,
            start_routing=self._routing_controller.start,
        )

    def on_set_api_key(self) -> None:
        """Prompt the user for a Google Maps API key and apply it for this session."""
        prompt_and_apply_api_key(
            root=self,
            maps_client=self._maps_client,
            env_path=resolve_env_file_path(),
            persist_env_var=upsert_env_var,
        )

    def on_cancel(self) -> None:
        """Cancel the current routing task if running."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin.on_cancel"
        try:
            self._routing_controller.cancel()
        except AppError as exc:
            raise ValidationError(location, str(exc)) from exc

    def on_open(self) -> None:
        """Open the generated route link in a browser."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin.on_open"
        try:
            open_route_link(self._runtime.route_link)
        except ValidationError as exc:
            raise ValidationError(location, str(exc)) from exc

    def on_copy(self) -> None:
        """Copy the route link to the clipboard."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin.on_copy"
        try:
            copy_route_link(
                self._runtime.route_link,
                clipboard_clear=self.clipboard_clear,
                clipboard_append=self.clipboard_append,
                parent=None,
            )
        except ValidationError as exc:
            raise ValidationError(location, str(exc)) from exc

    def on_export_csv(self) -> None:
        """Export the most recent route leg breakdown as a CSV file."""
        location = "fastest_route.presentation.gui.app.window_support.commands.RouteAppCommandMixin.on_export_csv"
        try:
            export_route_csv(
                root=self,
                request=self._runtime.last_request,
                result=self._runtime.last_result,
            )
        except ValidationError as exc:
            raise ValidationError(location, str(exc)) from exc

    def guided_entry(self) -> None:
        """Prompt for multiple addresses and populate stop inputs."""
        run_guided_entry(
            root=self,
            config=self._config,
            stop_entries=self._widgets.stops.stop_entries,
            set_visible_stops=self._widgets.stops.set_visible_stops,
            update_stop_counter=self._update_stop_counter,
            clear_status_labels=self._status_controller.clear_all,
            schedule_status_check=self._schedule_status_check,
        )
