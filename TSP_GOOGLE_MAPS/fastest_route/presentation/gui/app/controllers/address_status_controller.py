"""
Debounced address validation status updates for GUI entries.

Keeps validation feedback responsive while preventing UI thread blocking.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.controllers.address_status_logic import (
    compute_address_status,
)
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from fastest_route.config.registry import AppConfig
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient
    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState


class AddressStatusController:
    """
    Manage debounced background checks for address validity and status label updates.

    Provides quick feedback on input validity without risking UI thread freezes.
    """

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
        status_labels: list[ttk.Label],
    ) -> None:
        """Initialize the controller with required widget and service dependencies."""
        location = "fastest_route.presentation.gui.app.controllers.address_status_controller.AddressStatusController.__init__"
        if not root:
            raise ValidationError(location, "root is required.")
        if not config:
            raise ValidationError(location, "config is required.")
        if not maps_client:
            raise ValidationError(location, "maps_client is required.")
        if not runtime:
            raise ValidationError(location, "runtime is required.")
        if not status_labels:
            raise ValidationError(location, "status_labels is required.")
        self._root = root
        self._config = config
        self._maps_client = maps_client
        self._runtime = runtime
        self._start_entry = start_entry
        self._stop_entries = stop_entries
        self._end_entry = end_entry
        self._status_labels = status_labels
        self._end_idx = len(stop_entries) + 1
        self._generations: dict[int, int] = {}

    def clear_all(self) -> None:
        """Invalidate pending checks and clear every displayed address status."""

        location = (
            "fastest_route.presentation.gui.app.controllers.address_status_controller."
            "AddressStatusController.clear_all"
        )
        try:
            for idx, after_id in tuple(self._runtime.status_after_ids.items()):
                self._generations[idx] = self._generations.get(idx, 0) + 1
                self._root.after_cancel(after_id)
            self._runtime.status_after_ids.clear()
            for label in self._status_labels:
                label.config(text="", style="Status.Info.TLabel")
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to clear address statuses.") from exc

    def schedule(self, idx: int) -> None:
        """Debounce and schedule a status check for an entry index."""
        location = "fastest_route.presentation.gui.app.controllers.address_status_controller.AddressStatusController.schedule"
        try:
            if idx < 0 or idx > self._end_idx:
                raise ValidationError(location, "idx is outside the configured address fields.")
            generation = self._generations.get(idx, 0) + 1
            self._generations[idx] = generation
            if idx in self._runtime.status_after_ids:
                self._root.after_cancel(self._runtime.status_after_ids[idx])

            def run_check() -> None:
                """
                Spawn a background thread to update address status.

                Keeps geocoding out of the UI thread while the user types.
                """
                run_location = "fastest_route.presentation.gui.app.controllers.address_status_controller.AddressStatusController.schedule.run_check"
                try:
                    entry = self._entry_for_index(idx)
                    address_raw = entry.get()
                    label = self._status_labels[idx]
                    thread = threading.Thread(
                        target=self._update_address_status,
                        args=(idx, generation, address_raw, label),
                        daemon=True,
                    )
                    self._runtime.active_thread = thread
                    thread.start()
                except RuntimeError as exc:
                    raise ValidationError(
                        run_location, "Failed to start status check thread."
                    ) from exc

            self._runtime.status_after_ids[idx] = self._root.after(
                self._config.ui.status_delay_ms, run_check
            )
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to schedule status check.") from exc

    def _entry_for_index(self, idx: int) -> ttk.Entry:
        """Resolve the status-controller index to its input widget."""

        if idx == 0:
            return self._start_entry
        if idx == self._end_idx:
            return self._end_entry
        return self._stop_entries[idx - 1]

    def _update_address_status(
        self, idx: int, generation: int, address_raw: str, label: ttk.Label
    ) -> None:
        """Validate a single address and update its status label."""
        status = compute_address_status(maps_client=self._maps_client, address_raw=address_raw)
        self._update_status_label(idx, generation, label, status)

    def _update_status_label(self, idx: int, generation: int, label: ttk.Label, text: str) -> None:
        """
        Update a status label from the UI thread.

        Avoids thread-safety issues by ensuring UI changes occur on the Tk event loop thread.
        """
        location = "fastest_route.presentation.gui.app.controllers.address_status_controller.AddressStatusController._update_status_label"
        try:
            readable_text, style_name = _present_status(text)

            def apply_if_current() -> None:
                if self._generations.get(idx) == generation:
                    label.config(text=readable_text, style=style_name)

            self._root.after(0, apply_if_current)
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to update status label.") from exc


def _present_status(status_code: str) -> tuple[str, str]:
    """Convert low-level status codes into readable label text and semantic styles."""
    if status_code == "OK":
        return ("Valid", "Status.Ok.TLabel")
    if status_code == "KEY":
        return ("API key needed", "Status.Warn.TLabel")
    if status_code == "ERR":
        return ("Check input", "Status.Error.TLabel")
    if status_code == "SERVICE":
        return ("Service unavailable", "Status.Warn.TLabel")
    return ("", "Status.Info.TLabel")
