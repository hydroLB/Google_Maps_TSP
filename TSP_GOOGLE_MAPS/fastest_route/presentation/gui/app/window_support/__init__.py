"""Internal RouteApp mixins grouped by setup, appearance, commands, and lifecycle concerns."""

from fastest_route.presentation.gui.app.window_support.appearance import RouteAppAppearanceMixin
from fastest_route.presentation.gui.app.window_support.commands import RouteAppCommandMixin
from fastest_route.presentation.gui.app.window_support.lifecycle import RouteAppLifecycleMixin
from fastest_route.presentation.gui.app.window_support.setup import RouteAppSetupMixin

__all__ = [
    "RouteAppAppearanceMixin",
    "RouteAppCommandMixin",
    "RouteAppLifecycleMixin",
    "RouteAppSetupMixin",
]
