"""Tk window focus and positioning helpers for a predictable GUI experience."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress


def bring_to_front(window: tk.Tk | tk.Toplevel, *, y_divisor: int) -> None:
    """Center and raise a window, tolerating platform-specific Tk focus failures."""
    if y_divisor <= 0:
        y_divisor = 4
    with suppress(tk.TclError):
        window.update_idletasks()

    with suppress(tk.TclError):
        width = max(window.winfo_width(), 1)
        height = max(window.winfo_height(), 1)
        x = max((window.winfo_screenwidth() - width) // 2, 0)
        y = max((window.winfo_screenheight() - height) // y_divisor, 0)
        window.geometry(f"+{x}+{y}")

    with suppress(tk.TclError):
        window.lift()

    with suppress(tk.TclError):
        window.attributes("-topmost", True)

    with suppress(tk.TclError):
        window.after(50, lambda: window.attributes("-topmost", False))

    with suppress(tk.TclError):
        window.focus_force()
