"""Modal selection dialog for ambiguous geocoding results."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.views.components import (
    create_action_button,
    create_google_maps_attribution,
)
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens, resolve_theme_color
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def _pack_provider_attribution(*, root: tk.Misc, row_spacing: int) -> None:
    """Place Google Maps attribution beside provider-derived address choices."""
    create_google_maps_attribution(root=root).pack(anchor="e", pady=(0, row_spacing))


def select_address(root: tk.Tk, options: Sequence[str]) -> str | None:
    """Present a selection dialog for multiple address results."""
    location = "fastest_route.presentation.gui.app.dialogs.address_selection_dialog.select_address"
    if not root:
        raise ValidationError(location, "root is required.")
    try:
        tokens = get_theme_tokens()
        dialog = tk.Toplevel(root)
        dialog.title("Select Address")
        dialog.grab_set()
        dialog.transient(root)
        dialog.resizable(False, False)
        container = ttk.Frame(
            dialog,
            style="App.TFrame",
            padding=(tokens.window_padding_x, tokens.window_padding_y),
        )
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text="Multiple matches found. Select one:",
            style="SectionHeading.TLabel",
            anchor="w",
        ).pack(pady=(8, 2), anchor="w")
        list_frame = ttk.Frame(container, style="App.TFrame")
        list_frame.pack(
            pady=(2, 8),
            fill="both",
            expand=True,
        )
        listbox = tk.Listbox(
            list_frame,
            selectmode=tk.SINGLE,
            width=64,
            height=min(6, len(options)),
            bg=resolve_theme_color(role="surface.default"),
            fg=resolve_theme_color(role="text.primary"),
            selectbackground=resolve_theme_color(role="selection.background"),
            selectforeground=resolve_theme_color(role="selection.foreground"),
            highlightthickness=1,
            highlightbackground=resolve_theme_color(role="border.subtle"),
            highlightcolor=resolve_theme_color(role="border.focus"),
            relief="flat",
        )
        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            style="App.Vertical.TScrollbar",
            command=listbox.yview,
        )
        listbox.configure(yscrollcommand=scrollbar.set)
        for option in options:
            listbox.insert("end", option)
        if options:
            listbox.selection_set(0)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        _pack_provider_attribution(root=container, row_spacing=tokens.row_spacing)
        selection: dict[str, str | None] = {"value": None}

        def on_ok(_event: object | None = None) -> None:
            ok_location = "fastest_route.presentation.gui.app.dialogs.address_selection_dialog.select_address.on_ok"
            try:
                chosen_index: int | None = None
                for index in range(listbox.size()):
                    if listbox.selection_includes(index):
                        chosen_index = index
                        break
                if chosen_index is not None:
                    selection["value"] = listbox.get(chosen_index)
                dialog.destroy()
            except tk.TclError as exc:
                raise ValidationError(ok_location, "Failed to confirm address selection.") from exc

        def on_cancel(_event: object | None = None) -> None:
            cancel_location = "fastest_route.presentation.gui.app.dialogs.address_selection_dialog.select_address.on_cancel"
            try:
                selection["value"] = None
                dialog.destroy()
            except tk.TclError as exc:
                raise ValidationError(
                    cancel_location, "Failed to cancel address selection."
                ) from exc

        btn_frame = ttk.Frame(container, style="App.TFrame")
        btn_frame.pack(pady=(0, 8))
        btn_ok = create_action_button(
            root=btn_frame,
            text="OK",
            width=10,
            command=on_ok,
            is_primary=True,
        )
        btn_ok.pack(side="left", padx=tokens.inline_gap)
        create_action_button(
            root=btn_frame,
            text="Cancel",
            width=10,
            command=on_cancel,
            is_primary=False,
        ).pack(side="left", padx=tokens.inline_gap)
        if not options:
            btn_ok.configure(state="disabled")
        dialog.bind("<Return>", on_ok)
        dialog.bind("<Escape>", on_cancel)
        listbox.bind("<Double-Button-1>", on_ok)
        listbox.focus_set()
        dialog.wait_window()
        return selection["value"]
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to render selection dialog.") from exc
