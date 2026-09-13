"""Exact TSP solver using brute force permutation search.

Provides exact answers when the problem size is small."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from fastest_route.core.algorithms.validation import validate_square_matrix
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def brute_force_path(
    mtx: Sequence[Sequence[float]],
    *,
    start_index: int | None = None,
    end_index: int | None = None,
) -> tuple[list[int], float]:
    """Solve an open-path TSP variant by brute force enumeration.

    Provides an exact solution for small inputs and constrained path shapes."""
    location = "fastest_route.core.algorithms.brute_force.brute_force_path"
    validate_square_matrix(mtx, location=location)
    n = len(mtx)
    if start_index is not None and (start_index < 0 or start_index >= n):
        raise ValidationError(location, "start_index is out of range.")
    if end_index is not None and (end_index < 0 or end_index >= n):
        raise ValidationError(location, "end_index is out of range.")
    if start_index is not None and end_index is not None and start_index == end_index:
        raise ValidationError(location, "start_index and end_index must not be the same.")
    try:
        fixed: set[int] = set()
        if start_index is not None:
            fixed.add(start_index)
        if end_index is not None:
            fixed.add(end_index)
        variable = [idx for idx in range(n) if idx not in fixed]

        best_order: list[int] = []
        best_cost = float("inf")
        for perm in itertools.permutations(variable):
            order: list[int]
            if start_index is not None and end_index is not None:
                order = [start_index, *perm, end_index]
            elif start_index is not None:
                order = [start_index, *perm]
            elif end_index is not None:
                order = [*perm, end_index]
            else:
                order = list(perm)
            cost = sum(mtx[a][b] for a, b in zip(order, order[1:], strict=False))
            if cost < best_cost:
                best_cost, best_order = cost, order
        return best_order, best_cost
    except (IndexError, ValueError, TypeError) as exc:
        raise ValidationError(location, "Failed to compute brute force path route.") from exc


def brute_force_cycle(
    mtx: Sequence[Sequence[float]],
    *,
    start_index: int | None = None,
) -> tuple[list[int], float]:
    """Solve a round-trip (cycle) TSP variant by brute force enumeration.

    Provides an exact solution for small cycle routing problems."""
    location = "fastest_route.core.algorithms.brute_force.brute_force_cycle"
    validate_square_matrix(mtx, location=location)
    n = len(mtx)
    if start_index is not None and (start_index < 0 or start_index >= n):
        raise ValidationError(location, "start_index is out of range.")
    anchor = start_index if start_index is not None else 0
    try:
        variable = [idx for idx in range(n) if idx != anchor]
        best_order: list[int] = []
        best_cost = float("inf")
        for perm in itertools.permutations(variable):
            order = [anchor, *perm]
            legs = list(zip(order, order[1:], strict=False)) + [(order[-1], order[0])]
            cost = sum(mtx[a][b] for a, b in legs)
            if cost < best_cost:
                best_cost, best_order = cost, order
        return best_order, best_cost
    except (IndexError, ValueError, TypeError) as exc:
        raise ValidationError(location, "Failed to compute brute force cycle route.") from exc
