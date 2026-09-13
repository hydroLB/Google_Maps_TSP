from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from types import SimpleNamespace

from fastest_route.presentation.gui.app.controllers import (
    routing_controller as routing_controller_module,
)
from fastest_route.presentation.gui.app.controllers.routing_controller import RoutingController
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import CancellationError, ExternalServiceError
from fastest_route.shared.types import OptimizeFor, RouteKind, RouteRequest, TravelMode


@dataclass
class _Captured:
    error_title: str | None = None
    error_message: str | None = None
    cancelled_message: str | None = None


class _ImmediateRoot:
    def after(self, _delay_ms: int, callback) -> None:
        _ = _delay_ms
        callback()


def _build_controller_for_worker_tests(captured: _Captured) -> RoutingController:
    controller = RoutingController.__new__(RoutingController)
    controller._root = _ImmediateRoot()
    controller._correlation_context_factory = nullcontext
    controller._routing_service = object()
    controller._runtime = SimpleNamespace(task_cancel_token=None)
    controller._set_busy = lambda _busy: None
    controller._render_result = lambda *_args, **_kwargs: None
    controller._render_error = lambda title, message: (
        setattr(captured, "error_title", title),
        setattr(captured, "error_message", message),
    )
    controller._render_cancelled = lambda message: setattr(captured, "cancelled_message", message)
    return controller


def _sample_request() -> RouteRequest:
    return RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )


def test_worker_maps_external_service_error_to_external_title(monkeypatch) -> None:
    """Prevents ambiguous UI messages for external IO failures."""

    def raise_external(*_args, **_kwargs):
        raise ExternalServiceError("tests.worker", "provider failed")

    captured = _Captured()
    controller = _build_controller_for_worker_tests(captured)
    monkeypatch.setattr(routing_controller_module, "compute_route_artifacts", raise_external)

    token = CancellationToken()
    controller._runtime.task_cancel_token = token
    controller._compute_route_worker(_sample_request(), token)

    assert captured.error_title == "External Service Error"
    assert captured.error_message is not None
    assert captured.error_message.startswith("[E_EXTERNAL_IO] ")


def test_worker_maps_cancellation_to_cancelled_renderer(monkeypatch) -> None:
    """Ensures cancellation is not treated as a generic internal error."""

    def raise_cancelled(*_args, **_kwargs):
        raise CancellationError("tests.worker", "cancelled by user")

    captured = _Captured()
    controller = _build_controller_for_worker_tests(captured)
    monkeypatch.setattr(routing_controller_module, "compute_route_artifacts", raise_cancelled)

    token = CancellationToken()
    controller._runtime.task_cancel_token = token
    controller._compute_route_worker(_sample_request(), token)

    assert captured.cancelled_message is not None
    assert captured.cancelled_message.startswith("[E_CANCELLED] ")


def test_worker_maps_unknown_exceptions_to_internal_error(monkeypatch) -> None:
    """Prevents ambiguous unexpected-error rendering in worker jobs."""

    def raise_unknown(*_args, **_kwargs):
        raise RuntimeError("unexpected boom")

    captured = _Captured()
    controller = _build_controller_for_worker_tests(captured)
    monkeypatch.setattr(routing_controller_module, "compute_route_artifacts", raise_unknown)

    token = CancellationToken()
    controller._runtime.task_cancel_token = token
    controller._compute_route_worker(_sample_request(), token)

    assert captured.error_title == "Internal Error"
    assert captured.error_message is not None
    assert captured.error_message.startswith("[E_INTERNAL] ")
