"""Mutable runtime state for the GUI that is not part of the widget tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import threading
    import tkinter as tk
    from tkinter import ttk

    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import RouteRequest, RouteResult


@dataclass(slots=True)
class RouteAppRuntimeState:
    """Hold mutable runtime state used across controllers."""

    route_link: str | None = None
    last_request: RouteRequest | None = None
    last_result: RouteResult | None = None
    task_cancel_token: CancellationToken | None = None
    is_shutting_down: bool = False
    active_thread: threading.Thread | None = None
    autocomplete_popup: tk.Toplevel | None = None
    autocomplete_after_ids: dict[ttk.Entry, str] = field(default_factory=dict)
    status_after_ids: dict[int, str] = field(default_factory=dict)
