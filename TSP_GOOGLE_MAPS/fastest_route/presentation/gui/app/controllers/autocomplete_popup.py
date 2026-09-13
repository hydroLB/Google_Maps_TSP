"""Accessible popup rendering for Google Maps autocomplete suggestions."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.views.components import create_google_maps_attribution
from fastest_route.presentation.gui.app.views.theme import resolve_theme_color
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.presentation.gui.app.state.runtime import RouteAppRuntimeState


def hide_autocomplete_popup(*, runtime: RouteAppRuntimeState) -> None:
    """Destroy the active autocomplete popup, if one exists."""
    location = (
        "fastest_route.presentation.gui.app.controllers.autocomplete_popup.hide_autocomplete_popup"
    )
    popup = runtime.autocomplete_popup
    if popup is None:
        return
    try:
        runtime.autocomplete_popup = None
        if popup.winfo_exists():
            popup.destroy()
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to hide autocomplete suggestions.") from exc


def show_autocomplete_popup(
    *,
    root: tk.Tk,
    runtime: RouteAppRuntimeState,
    entry: ttk.Entry,
    suggestions: Sequence[str],
    entry_index: Callable[[ttk.Entry], int | None],
    schedule_status_check: Callable[[int], None],
) -> None:
    """Show attributed suggestions that support mouse and keyboard selection."""
    location = (
        "fastest_route.presentation.gui.app.controllers.autocomplete_popup.show_autocomplete_popup"
    )
    try:
        hide_autocomplete_popup(runtime=runtime)
        if not suggestions:
            return

        visible_rows = min(6, len(suggestions))
        popup_width = max(entry.winfo_width(), 340)
        popup_height = visible_rows * 24 + 36
        x = entry.winfo_rootx()
        y = entry.winfo_rooty() + entry.winfo_height()
        x = max(0, min(x, root.winfo_screenwidth() - popup_width))
        if y + popup_height > root.winfo_screenheight():
            y = max(0, entry.winfo_rooty() - popup_height)

        popup = tk.Toplevel(root)
        popup.overrideredirect(True)
        popup.transient(root)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        popup.configure(background=resolve_theme_color(role="border.subtle"))

        container = ttk.Frame(popup, style="App.TFrame", padding=(1, 1))
        container.pack(fill="both", expand=True)
        list_frame = ttk.Frame(container, style="App.TFrame")
        list_frame.pack(fill="both", expand=True)
        listbox = tk.Listbox(
            list_frame,
            height=visible_rows,
            width=1,
            exportselection=False,
            bg=resolve_theme_color(role="surface.default"),
            fg=resolve_theme_color(role="text.primary"),
            selectbackground=resolve_theme_color(role="selection.background"),
            selectforeground=resolve_theme_color(role="selection.foreground"),
            highlightthickness=1,
            highlightbackground=resolve_theme_color(role="border.subtle"),
            highlightcolor=resolve_theme_color(role="border.focus"),
            borderwidth=0,
            relief="flat",
            activestyle="none",
        )
        for suggestion in suggestions:
            listbox.insert("end", suggestion)
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            style="App.Vertical.TScrollbar",
            command=listbox.yview,
        )
        listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        create_google_maps_attribution(root=container).pack(fill="x", padx=(10, 10), pady=(3, 5))

        runtime.autocomplete_popup = popup

        def on_select(_event: object | None = None) -> str:
            try:
                selected_index: int | None = None
                for index in range(listbox.size()):
                    if listbox.selection_includes(index):
                        selected_index = index
                        break
                if selected_index is None:
                    return "break"
                chosen = listbox.get(selected_index)
                entry.delete(0, "end")
                entry.insert(0, chosen)
                hide_autocomplete_popup(runtime=runtime)
                idx = entry_index(entry)
                if idx is not None:
                    schedule_status_check(idx)
                entry.focus_set()
                entry.icursor("end")
                return "break"
            except (tk.TclError, ValueError) as exc:
                raise ValidationError(location, "Failed to apply autocomplete selection.") from exc

        def on_entry_down(_event: object) -> str:
            with suppress(tk.TclError):
                if runtime.autocomplete_popup is popup and popup.winfo_exists():
                    listbox.focus_set()
                    listbox.selection_set(0)
                    listbox.activate(0)
            return "break"

        def on_entry_escape(_event: object) -> str | None:
            if runtime.autocomplete_popup is not popup:
                return None
            with suppress(ValidationError, tk.TclError):
                hide_autocomplete_popup(runtime=runtime)
            return "break"

        def on_list_escape(_event: object) -> str:
            with suppress(ValidationError, tk.TclError):
                hide_autocomplete_popup(runtime=runtime)
                entry.focus_set()
            return "break"

        def hide_if_focus_left() -> None:
            with suppress(ValidationError, tk.TclError):
                focused = root.focus_get()
                if focused is entry or focused is listbox:
                    return
                if runtime.autocomplete_popup is popup:
                    hide_autocomplete_popup(runtime=runtime)

        def on_focus_out(_event: object) -> None:
            with suppress(tk.TclError):
                root.after_idle(hide_if_focus_left)

        entry_bindings: list[tuple[str, str]] = []
        for sequence, callback in (
            ("<Down>", on_entry_down),
            ("<Escape>", on_entry_escape),
            ("<FocusOut>", on_focus_out),
        ):
            bind_id = entry.bind(sequence, callback, add="+")
            if bind_id:
                entry_bindings.append((sequence, bind_id))

        def on_popup_destroy(event: object) -> None:
            if getattr(event, "widget", None) is not popup:
                return
            for sequence, bind_id in entry_bindings:
                with suppress(tk.TclError):
                    entry.unbind(sequence, bind_id)

        popup.bind("<Destroy>", on_popup_destroy, add="+")
        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        listbox.bind("<Escape>", on_list_escape)
        listbox.bind("<FocusOut>", on_focus_out, add="+")
    except (tk.TclError, ValueError, ValidationError) as exc:
        raise ValidationError(location, "Failed to display autocomplete suggestions.") from exc
