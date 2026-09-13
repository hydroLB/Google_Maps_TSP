"""Helpers for generating Google Maps route links."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.shared.types import TravelMode


def build_maps_link(
    addrs: Sequence[str],
    order: Sequence[int],
    mode: TravelMode,
    *,
    origin: str,
    destination: str,
    waypoints: Sequence[str],
) -> str:
    """Build a Google Maps directions link for a fully specified route."""
    location = "fastest_route.shared.utils.links.build_maps_link"
    try:
        if not addrs:
            raise ValidationError(location, "No addresses provided.")
        if not order:
            raise ValidationError(location, "No route order provided.")
        if len(order) != len(addrs):
            raise ValidationError(location, "Route order must include each address once.")
        if not isinstance(origin, str) or not origin.strip():
            raise ValidationError(location, "origin must be a non empty string.")
        if not isinstance(destination, str) or not destination.strip():
            raise ValidationError(location, "destination must be a non empty string.")
        for index in order:
            if not isinstance(index, int):
                raise ValidationError(location, "Route order indices must be integers.")
            if index < 0 or index >= len(addrs):
                raise ValidationError(location, "Route order indices are out of range.")
        params = {
            "api": 1,
            "origin": origin,
            "destination": destination,
            "travelmode": mode.value,
        }
        if waypoints:
            params["waypoints"] = "|".join(waypoints)
        return "https://www.google.com/maps/dir/?" + urlencode(params)
    except ValidationError:
        raise
    except (IndexError, TypeError, ValueError) as exc:
        raise ValidationError(location, "Failed to build maps link.") from exc


def build_route_link(
    addrs: Sequence[str],
    order: Sequence[int],
    mode: TravelMode,
    *,
    has_start: bool,
    has_end: bool,
    route_kind: str,
    start_resolved: str | None,
    end_resolved: str | None,
) -> str:
    """Build a Google Maps route link based on endpoint constraints and route shape."""
    location = "fastest_route.shared.utils.links.build_route_link"
    if not addrs:
        raise ValidationError(location, "No addresses provided.")
    if not order:
        raise ValidationError(location, "No route order provided.")
    if len(order) != len(addrs):
        raise ValidationError(location, "Route order must include each address once.")
    for index in order:
        if not isinstance(index, int):
            raise ValidationError(location, "Route order indices must be integers.")
        if index < 0 or index >= len(addrs):
            raise ValidationError(location, "Route order indices are out of range.")
    if has_start and start_resolved is None:
        raise ValidationError(location, "Start address is required when has_start is true.")
    if has_end and end_resolved is None:
        raise ValidationError(location, "End address is required when has_end is true.")
    try:
        start_value = start_resolved if start_resolved is not None else ""
        end_value = end_resolved if end_resolved is not None else ""
        ordered = [addrs[i] for i in order]
        if route_kind == "round_trip":
            if has_end:
                raise ValidationError(location, "Round trips do not support a fixed end address.")
            if has_start:
                if order[0] != 0:
                    raise ValidationError(location, "Route order must start with the fixed start.")
                origin = start_value
                destination = start_value
                waypoints = ordered[1:]
            else:
                origin = ordered[0]
                destination = origin
                waypoints = ordered[1:]
            return build_maps_link(
                addrs,
                order,
                mode,
                origin=origin,
                destination=destination,
                waypoints=waypoints,
            )

        if has_start and order[0] != 0:
            raise ValidationError(location, "Route order must start with the fixed start.")
        if has_end and order[-1] != len(addrs) - 1:
            raise ValidationError(location, "Route order must end with the fixed end.")

        origin = start_value if has_start else ordered[0]
        destination = end_value if has_end else ordered[-1]
        waypoints = ordered[1:-1]
        return build_maps_link(
            addrs,
            order,
            mode,
            origin=origin,
            destination=destination,
            waypoints=waypoints,
        )
    except ValidationError as exc:
        raise ValidationError(location, f"Failed to build route link. {exc}") from exc
    except (IndexError, TypeError, ValueError) as exc:
        raise ValidationError(
            location, "Failed to build route link due to invalid inputs."
        ) from exc
