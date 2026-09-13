"""Cache key helpers for distance lookups."""

from __future__ import annotations

import hashlib

from fastest_route.shared.errors import ValidationError

DISTANCE_CACHE_KEY_PREFIX = "distance:v2:"


def build_distance_key(
    origin: str,
    destination: str,
    mode: str,
    metric: str,
    *,
    departure_time: str | None = None,
    traffic_model: str | None = None,
) -> str:
    """Build a stable lookup key without persisting addresses in plaintext."""
    location = "fastest_route.infrastructure.cache.keys.build_distance_key"
    if not isinstance(origin, str) or not isinstance(destination, str):
        raise ValidationError(location, "Origin and destination must be strings.")
    if not isinstance(mode, str) or not isinstance(metric, str):
        raise ValidationError(location, "Mode and metric must be strings.")
    if not origin.strip() or not destination.strip():
        raise ValidationError(location, "Origin and destination must be set.")
    if not mode.strip() or not metric.strip():
        raise ValidationError(location, "Mode and metric must be set.")
    try:
        components = (
            mode,
            metric,
            departure_time or "",
            traffic_model or "",
            origin,
            destination,
        )
        normalized = "\x1f".join(" ".join(value.strip().lower().split()) for value in components)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{DISTANCE_CACHE_KEY_PREFIX}{digest}"
    except AttributeError as exc:
        raise ValidationError(location, "Failed to build cache key.") from exc
