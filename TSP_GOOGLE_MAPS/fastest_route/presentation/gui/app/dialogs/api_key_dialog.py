"""Modal dialog for configuring the Google Maps API key from the GUI."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from tkinter import ttk

from fastest_route.presentation.gui.app.dialogs.startup_dialog import normalize_api_key
from fastest_route.presentation.gui.app.utils.windowing import bring_to_front
from fastest_route.presentation.gui.app.views.components import create_action_button, create_entry
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens, resolve_theme_color
from fastest_route.shared.errors import ValidationError


def prompt_google_maps_api_key(*, root: tk.Tk) -> tuple[str, bool] | None:
    """Prompt the user to enter a Google Maps API key."""
    location = (
        "fastest_route.presentation.gui.app.dialogs.api_key_dialog.prompt_google_maps_api_key"
    )
    if not root:
        raise ValidationError(location, "root is required.")

    try:
        tokens = get_theme_tokens()
        dialog = tk.Toplevel(root)
        dialog.title("Add Google Maps API Key")
        dialog.transient(root)
        dialog.resizable(False, False)
        dialog.configure(background=resolve_theme_color(role="app.background"))

        container = ttk.Frame(
            dialog,
            style="App.TFrame",
            padding=(tokens.window_padding_x, tokens.window_padding_y),
        )
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Google Maps API key required",
            style="SectionHeading.TLabel",
            anchor="w",
        ).pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Autocomplete, address validation, and routing require a Google Maps API key.\n"
                "Paste your key below. The input is hidden by default."
            ),
            style="Muted.TLabel",
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(tokens.row_spacing, tokens.group_spacing))

        entry = create_entry(root=container)
        entry.configure(show="*", width=58)
        entry.pack(fill="x")

        show_var = tk.BooleanVar(value=False)

        def on_toggle_show() -> None:
            with suppress(tk.TclError):
                entry.configure(show="" if show_var.get() else "*")

        ttk.Checkbutton(
            container,
            text="Show key",
            variable=show_var,
            style="App.TCheckbutton",
            command=on_toggle_show,
        ).pack(anchor="w", pady=(tokens.row_spacing, 0))

        persist_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            container,
            text="Remember on this computer (.env, excluded from Git)",
            variable=persist_var,
            style="App.TCheckbutton",
        ).pack(anchor="w", pady=(tokens.row_spacing, 0))

        error_label = ttk.Label(container, text="", style="Status.Error.TLabel", anchor="w")
        error_label.pack(fill="x", pady=(tokens.row_spacing, 0))

        result: dict[str, object] = {"value": None, "persist": False}

        def on_apply() -> None:
            try:
                normalized = normalize_api_key(entry.get())
                result["value"] = normalized
                result["persist"] = bool(persist_var.get())
                dialog.destroy()
            except ValidationError as exc:
                error_label.configure(text=str(exc))
                return
            except tk.TclError:
                error_label.configure(text="Failed to apply API key.")
                return

        def on_cancel() -> None:
            with suppress(tk.TclError):
                dialog.destroy()

        button_row = ttk.Frame(container, style="App.TFrame")
        button_row.pack(anchor="e", pady=(tokens.group_spacing, 0))
        create_action_button(
            root=button_row,
            text="Cancel",
            width=12,
            command=on_cancel,
            is_primary=False,
        ).pack(side="right", padx=(tokens.inline_gap, 0))
        create_action_button(
            root=button_row,
            text="Apply",
            width=12,
            command=on_apply,
            is_primary=True,
        ).pack(side="right", padx=(0, tokens.inline_gap))

        dialog.bind("<Escape>", lambda _event: on_cancel())
        dialog.bind("<Return>", lambda _event: on_apply())
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        dialog.grab_set()
        bring_to_front(dialog, y_divisor=5)
        entry.focus_set()
        dialog.wait_window()

        value = result.get("value")
        if isinstance(value, str) and value:
            return value, bool(result.get("persist"))
        return None
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to render API key dialog.") from exc
