from __future__ import annotations

from dataclasses import dataclass

import pytest

from fastest_route.observability.metrics import (
    increment_counter,
    observe_duration_seconds,
    reset_metric_sink,
    set_metric_sink,
)
from fastest_route.presentation.gui.app.controllers.routing_job import compute_route_artifacts
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import OptimizeFor, RouteKind, RouteRequest, RouteResult, TravelMode


@dataclass
class _CapturedMetric:
    name: str
    value: float
    tags: dict[str, str]


class _CaptureSink:
    def __init__(self) -> None:
        self.counters: list[_CapturedMetric] = []
        self.durations: list[_CapturedMetric] = []

    def increment_counter(self, name: str, value: int, tags: dict[str, str]) -> None:
        self.counters.append(_CapturedMetric(name=name, value=float(value), tags=dict(tags)))

    def observe_duration_seconds(self, name: str, value: float, tags: dict[str, str]) -> None:
        self.durations.append(_CapturedMetric(name=name, value=float(value), tags=dict(tags)))


class _SuccessRoutingService:
    def compute_route(
        self, request: RouteRequest, *, cancellation_token
    ) -> RouteResult:  # pragma: no cover - exercised by tests
        _ = cancellation_token
        return RouteResult(order=[0, 1, 2], total=3.0, units="min", legs=[1.0, 2.0])


class _FailRoutingService:
    def compute_route(self, request: RouteRequest, *, cancellation_token) -> RouteResult:
        _ = request
        _ = cancellation_token
        raise ValidationError("tests.metrics", "forced failure")


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


def test_metric_helpers_reject_invalid_inputs() -> None:
    """Prevents malformed metrics from polluting sinks."""
    with pytest.raises(ValidationError):
        increment_counter("")
    with pytest.raises(ValidationError):
        increment_counter("metric", value=0)
    with pytest.raises(ValidationError):
        observe_duration_seconds("", value=0.1)
    with pytest.raises(ValidationError):
        observe_duration_seconds("metric", value=-1.0)


def test_compute_route_artifacts_emits_success_metrics() -> None:
    """Confirms metrics hooks are active on the critical routing success path."""
    sink = _CaptureSink()
    set_metric_sink(sink)
    try:
        route_link, summary, result = compute_route_artifacts(
            routing_service=_SuccessRoutingService(),
            request=_sample_request(),
            cancellation_token=object(),
        )
        assert isinstance(route_link, str)
        assert isinstance(summary, str)
        assert result.total == 3.0
        counter_names = [metric.name for metric in sink.counters]
        assert "routing.requests_total" in counter_names
        assert "routing.success_total" in counter_names
        assert len(sink.durations) == 1
        assert sink.durations[0].name == "routing.compute_duration_seconds"
    finally:
        reset_metric_sink()


def test_compute_route_artifacts_emits_failure_metrics() -> None:
    """Confirms metrics hooks remain active when routing fails."""
    sink = _CaptureSink()
    set_metric_sink(sink)
    try:
        with pytest.raises(ValidationError):
            compute_route_artifacts(
                routing_service=_FailRoutingService(),
                request=_sample_request(),
                cancellation_token=object(),
            )
        counter_names = [metric.name for metric in sink.counters]
        assert "routing.requests_total" in counter_names
        assert "routing.failure_total" in counter_names
        assert len(sink.durations) == 1
        assert sink.durations[0].name == "routing.compute_duration_seconds"
    finally:
        reset_metric_sink()
