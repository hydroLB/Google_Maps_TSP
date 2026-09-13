"""Export shared utility functions for address handling."""

from fastest_route.shared.utils.address_utils import (
    build_maps_link,
    build_route_link,
    generate_route_lines,
    normalize_address_input,
)

__all__ = [
    "normalize_address_input",
    "build_maps_link",
    "build_route_link",
    "generate_route_lines",
]
