"""Minimal metrics hook surface for counters and duration observations."""

from __future__ import annotations

from typing import Protocol

from fastest_route.shared.errors import ValidationError


class MetricSink(Protocol):
    """Runtime contract for metric sinks."""

    def increment_counter(self, name: str, value: int, tags: dict[str, str]) -> None: ...

    def observe_duration_seconds(self, name: str, value: float, tags: dict[str, str]) -> None: ...


class NullMetricSink:
    """Default no-op metric sink."""

    def increment_counter(self, name: str, value: int, tags: dict[str, str]) -> None:
        """Ignore counter increments."""
        _ = name
        _ = value
        _ = tags

    def observe_duration_seconds(self, name: str, value: float, tags: dict[str, str]) -> None:
        """Ignore duration observations."""
        _ = name
        _ = value
        _ = tags


_METRIC_SINK: MetricSink = NullMetricSink()


def set_metric_sink(sink: MetricSink) -> None:
    """Set the global metric sink used by instrumentation helpers."""
    location = "fastest_route.observability.metrics.set_metric_sink"
    if sink is None:
        raise ValidationError(location, "sink is required.")
    if not callable(getattr(sink, "increment_counter", None)):
        raise ValidationError(location, "sink must define increment_counter.")
    if not callable(getattr(sink, "observe_duration_seconds", None)):
        raise ValidationError(location, "sink must define observe_duration_seconds.")
    global _METRIC_SINK
    _METRIC_SINK = sink


def reset_metric_sink() -> None:
    """Reset global metric sink to the default no-op sink."""
    global _METRIC_SINK
    _METRIC_SINK = NullMetricSink()


def increment_counter(name: str, *, value: int = 1, tags: dict[str, str] | None = None) -> None:
    """Emit a counter increment through the active metric sink."""
    location = "fastest_route.observability.metrics.increment_counter"
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(location, "name must be a non empty string.")
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(location, "value must be a positive integer.")
    safe_tags = dict(tags or {})
    _METRIC_SINK.increment_counter(name.strip(), value, safe_tags)


def observe_duration_seconds(
    name: str, *, value: float, tags: dict[str, str] | None = None
) -> None:
    """Emit a duration observation through the active metric sink."""
    location = "fastest_route.observability.metrics.observe_duration_seconds"
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(location, "name must be a non empty string.")
    if not isinstance(value, int | float) or value < 0:
        raise ValidationError(location, "value must be a non negative number.")
    safe_tags = dict(tags or {})
    _METRIC_SINK.observe_duration_seconds(name.strip(), float(value), safe_tags)
