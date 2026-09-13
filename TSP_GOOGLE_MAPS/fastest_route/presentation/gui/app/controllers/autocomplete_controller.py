"""Debounced, stale-safe autocomplete orchestration for address entries."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.observability.logger import get_logger
from fastest_route.presentation.gui.app.controllers.autocomplete_popup import (
    hide_autocomplete_popup,
    show_autocomplete_popup,
)
from fastest_route.shared.errors import ExternalServiceError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.config.registry import AppConfig
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState

logger = get_logger(__name__, component="gui.autocomplete")


def should_display_autocomplete_results(
    *,
    expected_query: str,
    current_query: str,
    expected_generation: int,
    active_generation: int,
    entry_has_focus: bool,
) -> bool:
    """Return whether an asynchronous response still matches the active field state."""
    return (
        bool(expected_query)
        and expected_query == current_query
        and expected_generation == active_generation
        and entry_has_focus
    )


class AutocompleteController:
    """Fetch and render address suggestions without retaining provider prediction lists."""

    def __init__(
        self,
        *,
        root: tk.Tk,
        config: AppConfig,
        maps_client: GoogleMapsClient,
        runtime: RouteAppRuntimeState,
        start_entry: ttk.Entry,
        stop_entries: list[ttk.Entry],
        end_entry: ttk.Entry,
        schedule_status_check: Callable[[int], None],
    ) -> None:
        location = (
            "fastest_route.presentation.gui.app.controllers.autocomplete_controller."
            "AutocompleteController.__init__"
        )
        if not root:
            raise ValidationError(location, "root is required.")
        if not config:
            raise ValidationError(location, "config is required.")
        if not maps_client:
            raise ValidationError(location, "maps_client is required.")
        if not runtime:
            raise ValidationError(location, "runtime is required.")
        self._root = root
        self._config = config
        self._maps_client = maps_client
        self._runtime = runtime
        self._start_entry = start_entry
        self._stop_entries = stop_entries
        self._end_entry = end_entry
        self._end_idx = len(stop_entries) + 1
        self._schedule_status_check = schedule_status_check
        self._request_generation = 0
        self._scheduled_queries: dict[ttk.Entry, str] = {}

    def schedule(self, entry: ttk.Entry) -> None:
        """Debounce autocomplete and invalidate responses from older input states."""
        location = (
            "fastest_route.presentation.gui.app.controllers.autocomplete_controller."
            "AutocompleteController.schedule"
        )
        try:
            query = entry.get().strip()
            if self._scheduled_queries.get(entry) == query:
                return
            self._scheduled_queries[entry] = query
            self._request_generation += 1
            generation = self._request_generation
            self.hide()
            pending_id = self._runtime.autocomplete_after_ids.get(entry)
            if pending_id is not None:
                self._root.after_cancel(pending_id)

            def run() -> None:
                if len(query) < self._config.ui.autocomplete_min_chars:
                    self.hide()
                    return
                self._start_fetch(entry=entry, query=query, generation=generation)

            self._runtime.autocomplete_after_ids[entry] = self._root.after(
                self._config.ui.autocomplete_delay_ms, run
            )
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to schedule autocomplete.") from exc

    def hide(self) -> None:
        """Hide any active suggestion popup."""
        try:
            hide_autocomplete_popup(runtime=self._runtime)
        except ValidationError as exc:
            raise ValidationError(
                "fastest_route.presentation.gui.app.controllers.autocomplete_controller."
                "AutocompleteController.hide",
                exc.message,
            ) from exc

    def _start_fetch(self, *, entry: ttk.Entry, query: str, generation: int) -> None:
        thread = threading.Thread(
            target=self._fetch_and_show,
            args=(entry, query, generation),
            daemon=True,
        )
        self._runtime.active_thread = thread
        thread.start()

    def _fetch_and_show(self, entry: ttk.Entry, query: str, generation: int) -> None:
        """Fetch one current-query response and schedule its guarded UI update."""
        try:
            if not self._maps_client.has_api_key():
                return
            suggestions = self._maps_client.autocomplete(query)
            self._root.after(
                0,
                lambda: self._show_if_current(
                    entry=entry,
                    query=query,
                    generation=generation,
                    suggestions=suggestions,
                ),
            )
        except (ExternalServiceError, ValidationError, tk.TclError) as exc:
            logger.error("Autocomplete failed", extra={"error": str(exc)})

    def _show_if_current(
        self,
        *,
        entry: ttk.Entry,
        query: str,
        generation: int,
        suggestions: Sequence[str],
    ) -> None:
        try:
            if not entry.winfo_exists():
                return
            if not should_display_autocomplete_results(
                expected_query=query,
                current_query=entry.get().strip(),
                expected_generation=generation,
                active_generation=self._request_generation,
                entry_has_focus=self._root.focus_get() is entry,
            ):
                return
            self._show_list(entry, suggestions)
        except tk.TclError:
            return

    def _show_list(self, entry: ttk.Entry, suggestions: Sequence[str]) -> None:
        try:
            show_autocomplete_popup(
                root=self._root,
                runtime=self._runtime,
                entry=entry,
                suggestions=suggestions,
                entry_index=self._entry_index,
                schedule_status_check=self._schedule_status_check,
            )
        except ValidationError as exc:
            raise ValidationError(
                "fastest_route.presentation.gui.app.controllers.autocomplete_controller."
                "AutocompleteController._show_list",
                exc.message,
            ) from exc

    def _entry_index(self, entry: ttk.Entry) -> int | None:
        if entry is self._start_entry:
            return 0
        if entry is self._end_entry:
            return self._end_idx
        try:
            return self._stop_entries.index(entry) + 1
        except ValueError:
            return None
