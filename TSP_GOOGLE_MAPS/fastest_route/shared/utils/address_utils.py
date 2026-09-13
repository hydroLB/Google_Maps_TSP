"""Cohesive import surface for address utilities."""

from __future__ import annotations

from fastest_route.shared.utils.links import build_maps_link, build_route_link
from fastest_route.shared.utils.normalization import normalize_address_input
from fastest_route.shared.utils.presenters import generate_route_lines

__all__ = [
    "normalize_address_input",
    "build_maps_link",
    "build_route_link",
    "generate_route_lines",
]
