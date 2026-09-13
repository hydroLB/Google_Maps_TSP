"""RouteApp appearance and responsive-density behavior."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.utils.windowing import bring_to_front
from fastest_route.presentation.gui.app.views.theme import (
    apply_density_profile,
    apply_theme,
    detect_system_appearance,
    get_theme_tokens,
    is_compact_window_size,
    should_follow_system_theme,
)
from fastest_route.presentation.gui.app.window_support.base import RouteAppHost
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from fastest_route.presentation.gui.app.views.theme import GuiThemeTokens


class RouteAppAppearanceMixin(RouteAppHost):
    """Provide RouteApp methods related to theme following and responsive density."""

    def _start_os_theme_follow(self) -> None:
        """Start polling for OS appearance changes when the GUI is configured to follow the system."""
        if not should_follow_system_theme(preference=self._config.ui.theme_mode):
            return
        poll_seconds = self._config.ui.os_theme_poll_seconds
        poll_ms = int(poll_seconds * 1000)
        if poll_ms <= 0:
            return
        self._os_theme_poll_ms = poll_ms
        self.after(self._os_theme_poll_ms, self._poll_os_theme)

    def _poll_os_theme(self) -> None:
        """Poll the OS appearance and apply theme updates when it changes."""
        with suppress(tk.TclError, ValidationError):
            if self._runtime.is_shutting_down:
                return
            detected = detect_system_appearance()
            if detected is not None and detected != getattr(self, "_applied_appearance", None):
                apply_theme(root=self, appearance=detected)
                compact = getattr(self, "_is_compact_density", None)
                if compact is not None:
                    apply_density_profile(root=self, compact=compact)
                self._applied_appearance = detected
            self.after(getattr(self, "_os_theme_poll_ms", 2000), self._poll_os_theme)

    def _start_responsive_density_follow(self) -> None:
        """Start listening to window-size changes to toggle compact UI density."""
        with suppress(tk.TclError):
            self.bind("<Configure>", self._on_window_resize, add="+")
            self.after(0, self._apply_density_for_current_size)

    def _on_window_resize(self, _event: object) -> None:
        """Handle window resize events and refresh responsive density."""
        with suppress(tk.TclError, ValidationError):
            self._apply_density_for_current_size()

    def _apply_density_for_current_size(self) -> None:
        """Apply compact or standard density based on the current window dimensions."""
        location = "fastest_route.presentation.gui.app.window_support.appearance.RouteAppAppearanceMixin._apply_density_for_current_size"
        try:
            tokens = get_theme_tokens()
            width = int(self.winfo_width())
            height = int(self.winfo_height())
            compact = is_compact_window_size(width=width, height=height, tokens=tokens)
            if compact == self._is_compact_density:
                return
            self._is_compact_density = compact
            apply_density_profile(root=self, compact=compact)
            self._configure_output_density(compact=compact, tokens=tokens)
            self._configure_action_button_widths(compact=compact, tokens=tokens)
            self._configure_entry_widths(compact=compact, tokens=tokens)
        except tk.TclError as exc:
            raise ValidationError(location, "Failed to apply responsive density profile.") from exc

    def _configure_output_density(self, *, compact: bool, tokens: GuiThemeTokens) -> None:
        """Apply output panel sizing for the active density mode."""
        output_rows = tokens.compact_output_height_rows if compact else tokens.output_height_rows
        self._widgets.output.text.configure(height=output_rows)

    def _configure_action_button_widths(self, *, compact: bool, tokens: GuiThemeTokens) -> None:
        """Apply action and link button widths for the active density mode."""
        primary_width = (
            tokens.compact_button_width_primary if compact else tokens.button_width_primary
        )
        secondary_width = (
            tokens.compact_button_width_secondary if compact else tokens.button_width_secondary
        )
        for button in (
            self._widgets.actions.btn_optimize,
            self._widgets.actions.btn_guided,
        ):
            button.configure(width=primary_width)
        for button in (
            self._widgets.actions.btn_api_key,
            self._widgets.actions.btn_cancel,
            self._widgets.links.btn_open,
            self._widgets.links.btn_copy,
            self._widgets.links.btn_export,
        ):
            button.configure(width=secondary_width)

    def _configure_entry_widths(self, *, compact: bool, tokens: GuiThemeTokens) -> None:
        """Apply start, stop, and end entry widths for the active density mode."""
        key_width = tokens.entry_width_key_compact if compact else tokens.entry_width_key
        row_width = tokens.entry_width_standard_compact if compact else tokens.entry_width_standard
        self._widgets.stops.start_entry.configure(width=key_width)
        self._widgets.stops.end_entry.configure(width=key_width)
        for stop_entry in self._widgets.stops.stop_entries:
            stop_entry.configure(width=row_width)

    def _show_window(self) -> None:
        """Raise and focus the window without failing on window-manager quirks."""
        bring_to_front(self, y_divisor=6)
        with suppress(tk.TclError):
            self._widgets.stops.start_entry.focus_set()
