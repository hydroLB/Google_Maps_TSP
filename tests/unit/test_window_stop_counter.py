from __future__ import annotations

from fastest_route.presentation.gui.app.window import RouteApp


def test_update_stop_counter_is_noop_before_widgets() -> None:
    """Startup should not fail when the stop-counter callback runs before self._widgets is assigned."""

    class Dummy:
        pass

    RouteApp._update_stop_counter(Dummy())
