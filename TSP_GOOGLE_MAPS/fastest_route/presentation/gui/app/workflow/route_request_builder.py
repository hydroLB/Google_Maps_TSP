"""Build validated routing requests from raw presentation input."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import OptimizeFor, RouteKind, RouteRequest, TravelMode

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.config.registry import AppConfig


def build_route_request(
    *,
    config: AppConfig,
    start_raw: str,
    end_raw: str,
    stop_raws: Sequence[str],
    mode_value: str,
    optimize_value: str,
    trip_value: str,
    geocode: Callable[[str], str],
    normalize: Callable[[str], str],
) -> RouteRequest:
    """Validate local form constraints, then geocode and assemble a request."""
    location = (
        "fastest_route.presentation.gui.app.workflow.route_request_builder.build_route_request"
    )
    if not config:
        raise ValidationError(location, "config is required.")
    if not callable(geocode):
        raise ValidationError(location, "geocode must be callable.")
    if not callable(normalize):
        raise ValidationError(location, "normalize must be callable.")
    try:
        start_value = start_raw.strip()
        end_value = end_raw.strip()
        raw_stops = [
            value.strip() for value in stop_raws if isinstance(value, str) and value.strip()
        ]
        if len(raw_stops) < config.ui.min_stops:
            raise ValidationError(location, "Not enough stops to compute a route.")
        if len(raw_stops) > config.ui.max_stops:
            raise ValidationError(location, "Too many stops for the configured UI limits.")

        mode = TravelMode(mode_value)
        metric = OptimizeFor(optimize_value)
        route_kind = RouteKind(trip_value)
        if route_kind == RouteKind.ROUND_TRIP and end_value:
            raise ValidationError(
                location, "Round trips do not support a fixed end. Clear the End field."
            )

        # Reject purely local form errors before spending quota or blocking on geocoding.
        start_resolved = geocode(normalize(start_value)) if start_value else None
        resolved_stops = [geocode(normalize(raw)) for raw in raw_stops]
        end_resolved = geocode(normalize(end_value)) if end_value else None
        has_start = start_resolved is not None
        has_end = end_resolved is not None

        addresses: list[str] = []
        originals: list[str] = []
        if has_start and start_resolved is not None:
            addresses.append(start_resolved)
            originals.append(start_value)
        addresses.extend(resolved_stops)
        originals.extend(raw_stops)
        if has_end and end_resolved is not None:
            addresses.append(end_resolved)
            originals.append(end_value)

        return RouteRequest(
            addresses=addresses,
            originals=originals,
            mode=mode,
            optimize_for=metric,
            has_start=has_start,
            has_end=has_end,
            route_kind=route_kind,
        )
    except ValueError as exc:
        raise ValidationError(location, "Invalid mode, optimize_for, or trip selection.") from exc
    except ValidationError:
        raise
    except (TypeError, AttributeError) as exc:
        raise ValidationError(
            location, "Failed to build RouteRequest due to invalid inputs."
        ) from exc
