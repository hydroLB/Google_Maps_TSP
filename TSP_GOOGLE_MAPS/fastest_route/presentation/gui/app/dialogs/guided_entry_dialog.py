"""Modal multiline stop-import dialog for the desktop application."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from tkinter import ttk

from fastest_route.presentation.gui.app.utils.windowing import bring_to_front
from fastest_route.presentation.gui.app.views.components import create_action_button
from fastest_route.presentation.gui.app.views.theme import get_theme_tokens, resolve_theme_color
from fastest_route.presentation.gui.app.workflow.guided_entry_parser import parse_guided_entry_lines
from fastest_route.shared.errors import ValidationError


def prompt_guided_entry(*, root: tk.Tk, min_stops: int, max_stops: int) -> list[str] | None:
    """Collect and validate one stop per line, returning ``None`` when cancelled."""
    location = "fastest_route.presentation.gui.app.dialogs.guided_entry_dialog.prompt_guided_entry"
    if not root:
        raise ValidationError(location, "root is required.")

    try:
        tokens = get_theme_tokens()
        dialog = tk.Toplevel(root)
        dialog.title("Import Stops")
        dialog.transient(root)
        dialog.minsize(560, 390)
        dialog.geometry("620x440")
        dialog.configure(background=resolve_theme_color(role="app.background"))

        container = ttk.Frame(
            dialog,
            style="App.TFrame",
            padding=(tokens.window_padding_x, tokens.window_padding_y),
        )
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Paste your stops",
            style="SectionHeading.TLabel",
            anchor="w",
        ).pack(anchor="w")
        ttk.Label(
            container,
            text=(
                f"Enter one stop per line ({min_stops} minimum, {max_stops} maximum). "
                "Start and end locations remain optional fields in the main window."
            ),
            style="Muted.TLabel",
            anchor="w",
            justify="left",
            wraplength=570,
        ).pack(anchor="w", pady=(tokens.row_spacing, tokens.group_spacing))

        editor_frame = ttk.Frame(container, style="Section.Content.TFrame", padding=(1, 1))
        editor_frame.pack(fill="both", expand=True)
        editor = tk.Text(
            editor_frame,
            height=12,
            width=64,
            wrap="word",
            undo=True,
            takefocus=True,
            padx=tokens.control_spacing,
            pady=tokens.control_spacing,
            bg=resolve_theme_color(role="output.background"),
            fg=resolve_theme_color(role="text.primary"),
            insertbackground=resolve_theme_color(role="text.primary"),
            selectbackground=resolve_theme_color(role="selection.background"),
            selectforeground=resolve_theme_color(role="selection.foreground"),
            highlightthickness=1,
            highlightbackground=resolve_theme_color(role="border.subtle"),
            highlightcolor=resolve_theme_color(role="border.focus"),
            relief="flat",
        )
        scrollbar = ttk.Scrollbar(
            editor_frame,
            orient="vertical",
            style="App.Vertical.TScrollbar",
            command=editor.yview,
        )
        editor.configure(yscrollcommand=scrollbar.set)
        editor.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        error_label = ttk.Label(container, text="", style="Status.Error.TLabel", anchor="w")
        error_label.pack(fill="x", pady=(tokens.row_spacing, 0))

        result: dict[str, list[str] | None] = {"stops": None}

        def on_import() -> None:
            try:
                result["stops"] = parse_guided_entry_lines(
                    raw_text=editor.get("1.0", "end-1c"),
                    min_stops=min_stops,
                    max_stops=max_stops,
                )
                dialog.destroy()
            except ValidationError as exc:
                error_label.configure(text=exc.message)
                editor.focus_set()
            except tk.TclError:
                error_label.configure(text="Unable to read the pasted stops.")

        def on_cancel() -> None:
            with suppress(tk.TclError):
                dialog.destroy()

        def on_import_shortcut(_event: object) -> str:
            on_import()
            return "break"

        def on_cancel_shortcut(_event: object) -> str:
            on_cancel()
            return "break"

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
            text="Import Stops",
            width=15,
            command=on_import,
            is_primary=True,
        ).pack(side="right", padx=(0, tokens.inline_gap))

        dialog.bind("<Escape>", on_cancel_shortcut)
        dialog.bind("<Control-Return>", on_import_shortcut)
        dialog.bind("<Command-Return>", on_import_shortcut)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.grab_set()
        bring_to_front(dialog, y_divisor=5)
        editor.focus_set()
        dialog.wait_window()
        return result["stops"]
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to render the stop import dialog.") from exc
