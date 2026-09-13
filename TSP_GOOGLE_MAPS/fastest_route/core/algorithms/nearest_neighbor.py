"""Nearest neighbor heuristic for approximate TSP solutions.

Provides a fast route when exact search is too costly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.core.algorithms.validation import validate_square_matrix
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def nearest_neighbor(mtx: Sequence[Sequence[float]], *, start_index: int) -> list[int]:
    """Build a TSP route with the nearest neighbor heuristic.

    Produces a quick baseline route for larger inputs."""
    location = "fastest_route.core.algorithms.nearest_neighbor.nearest_neighbor"
    validate_square_matrix(mtx, location=location)
    if start_index < 0 or start_index >= len(mtx):
        raise ValidationError(location, "start_index is out of range.")
    try:
        unvisited = set(range(len(mtx)))
        route = [start_index]
        unvisited.remove(start_index)
        while unvisited:
            last = route[-1]
            next_index = min(unvisited, key=lambda j: mtx[last][j])
            unvisited.remove(next_index)
            route.append(next_index)
        return route
    except (IndexError, ValueError, TypeError) as exc:
        raise ValidationError(location, "Failed to compute nearest neighbor route.") from exc


def nearest_neighbor_with_fixed_end(
    mtx: Sequence[Sequence[float]],
    *,
    start_index: int,
    end_index: int,
) -> list[int]:
    """Build an open-path route with a fixed start and fixed end using a greedy heuristic.

    Provides a fast, constraint-aware baseline when exact search is too costly."""
    location = "fastest_route.core.algorithms.nearest_neighbor.nearest_neighbor_with_fixed_end"
    validate_square_matrix(mtx, location=location)
    if start_index < 0 or start_index >= len(mtx):
        raise ValidationError(location, "start_index is out of range.")
    if end_index < 0 or end_index >= len(mtx):
        raise ValidationError(location, "end_index is out of range.")
    if start_index == end_index:
        raise ValidationError(location, "start_index and end_index must not be the same.")
    try:
        unvisited = set(range(len(mtx)))
        unvisited.remove(start_index)
        unvisited.remove(end_index)
        route = [start_index]
        while unvisited:
            last = route[-1]
            next_index = min(unvisited, key=lambda j: mtx[last][j])
            unvisited.remove(next_index)
            route.append(next_index)
        route.append(end_index)
        return route
    except (IndexError, ValueError, TypeError) as exc:
        raise ValidationError(location, "Failed to compute nearest neighbor route.") from exc
