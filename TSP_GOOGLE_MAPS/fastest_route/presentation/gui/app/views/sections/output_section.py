"""Widget builder for the output text area."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from fastest_route.presentation.gui.app.state.widgets import OutputSectionWidgets
from fastest_route.presentation.gui.app.views.components import (
    create_google_maps_attribution,
    create_section_frame,
    create_status_label,
)
from fastest_route.presentation.gui.app.views.theme import (
    get_theme_tokens,
    resolve_status_style,
    resolve_theme_color,
)
from fastest_route.shared.errors import ValidationError


def build_output_section(*, root: tk.Misc) -> OutputSectionWidgets:
    """Build the output text area."""
    location = (
        "fastest_route.presentation.gui.app.views.sections.output_section.build_output_section"
    )
    if not root:
        raise ValidationError(location, "root is required.")
    try:
        tokens = get_theme_tokens()
        frame_out = create_section_frame(root=root, title="Optimized route")
        frame_out.pack(fill="both", expand=True, pady=(0, tokens.group_spacing))
        header = ttk.Frame(frame_out, style="App.TFrame")
        header.pack(fill="x", padx=(0, 2), pady=(0, tokens.row_spacing))
        ttk.Label(header, text="Route summary", style="SectionHeading.TLabel").pack(side="left")
        status_label = create_status_label(root=header)
        status_label.configure(text="Ready", style=resolve_status_style(status_text="Ready"))
        status_label.pack(side="right")

        body = ttk.Frame(frame_out, style="Section.Content.TFrame", padding=(1, 1))
        body.pack(fill="both", expand=True)
        txt_out = tk.Text(
            body,
            height=tokens.output_height_rows,
            width=tokens.output_width_chars,
            state="normal",
            wrap="word",
            cursor="arrow",
            takefocus=True,
            padx=tokens.control_spacing,
            pady=tokens.control_spacing,
            bg=resolve_theme_color(role="output.background"),
            fg=resolve_theme_color(role="text.primary"),
            highlightthickness=1,
            highlightbackground=resolve_theme_color(role="border.subtle"),
            highlightcolor=resolve_theme_color(role="border.focus"),
            relief="flat",
        )
        txt_out.insert(
            "end",
            "No route has been generated yet.\n\nAdd your stops and click Optimize Route.",
        )
        txt_out.configure(state="disabled")

        def select_all_output(_event: object) -> str:
            txt_out.tag_add("sel", "1.0", "end-1c")
            return "break"

        def copy_output(_event: object) -> str:
            txt_out.event_generate("<<Copy>>")
            return "break"

        for shortcut in ("<Control-a>", "<Command-a>"):
            txt_out.bind(shortcut, select_all_output)
        for shortcut in ("<Control-c>", "<Command-c>"):
            txt_out.bind(shortcut, copy_output)
        scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            style="App.Vertical.TScrollbar",
            command=txt_out.yview,
        )
        txt_out.configure(yscrollcommand=scrollbar.set)
        txt_out.pack(side="left", fill="both", expand=True, padx=(0, tokens.inline_gap), pady=2)
        scrollbar.pack(side="right", fill="y")
        create_google_maps_attribution(root=frame_out).pack(
            anchor="e", pady=(tokens.row_spacing, 0)
        )
        return OutputSectionWidgets(text=txt_out, status_label=status_label)
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to initialize output section.") from exc
