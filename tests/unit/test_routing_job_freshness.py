"""Regression tests for routing-job identity and stale callback suppression."""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from fastest_route.presentation.gui.app.controllers import (
    routing_controller as routing_controller_module,
)
from fastest_route.presentation.gui.app.controllers.routing_controller import RoutingController
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import CancellationError
from fastest_route.shared.types import OptimizeFor, RouteKind, RouteRequest, TravelMode


class _QueuedRoot:
    """Tk root double that retains callbacks until the test flushes them."""

    def __init__(self) -> None:
        self.callbacks = []

    def after(self, _delay_ms: int, callback) -> None:
        """Queue a Tk callback without executing it."""
        self.callbacks.append(callback)

    def flush(self) -> None:
        """Execute all queued callbacks in scheduling order."""
        while self.callbacks:
            self.callbacks.pop(0)()


def _sample_request() -> RouteRequest:
    """Return a minimal request accepted by the worker boundary."""
    return RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )


def _controller(events: list[str], token: CancellationToken) -> RoutingController:
    """Build a controller with observable render and busy-state boundaries."""
    controller = RoutingController.__new__(RoutingController)
    controller._root = _QueuedRoot()
    controller._correlation_context_factory = nullcontext
    controller._routing_service = object()
    controller._runtime = SimpleNamespace(task_cancel_token=token)
    controller._set_busy = lambda busy: events.append(f"busy:{busy}")
    controller._render_result = lambda *_args: events.append("result")
    controller._render_error = lambda *_args: events.append("error")
    controller._render_cancelled = lambda *_args: events.append("cancelled")
    return controller


def test_completed_stale_job_cannot_render_or_unlock_new_job(monkeypatch) -> None:
    """A completed job's queued callbacks must not mutate a replacement job's UI."""
    first_token = CancellationToken()
    events: list[str] = []
    controller = _controller(events, first_token)
    monkeypatch.setattr(
        routing_controller_module,
        "compute_route_artifacts",
        lambda **_kwargs: ("route-link", "summary", object()),
    )

    controller._compute_route_worker(_sample_request(), first_token)
    second_token = CancellationToken()
    controller._runtime.task_cancel_token = second_token
    controller._root.flush()

    assert events == []
    assert controller._runtime.task_cancel_token is second_token


def test_cancelled_job_cannot_render_or_unlock_new_job(monkeypatch) -> None:
    """Cancellation from an old job must not overwrite a replacement job's UI."""

    def raise_cancelled(**_kwargs):
        raise CancellationError("tests.worker", "cancelled")

    first_token = CancellationToken()
    events: list[str] = []
    controller = _controller(events, first_token)
    monkeypatch.setattr(routing_controller_module, "compute_route_artifacts", raise_cancelled)

    controller._compute_route_worker(_sample_request(), first_token)
    second_token = CancellationToken()
    controller._runtime.task_cancel_token = second_token
    controller._root.flush()

    assert events == []
    assert controller._runtime.task_cancel_token is second_token


def test_cancel_invalidates_job_identity_while_signalling_worker() -> None:
    """Cancel cooperatively signals the worker and makes its callbacks stale."""
    token = CancellationToken()
    events: list[str] = []
    controller = _controller(events, token)

    controller.cancel()

    assert token.is_cancelled()
    assert controller._runtime.task_cancel_token is None
    assert events == ["busy:False"]
