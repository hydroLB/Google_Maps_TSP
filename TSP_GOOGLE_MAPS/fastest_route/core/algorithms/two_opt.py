"""Two opt heuristic for improving an existing route.

Refinement step that reduces route cost efficiently."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.core.algorithms.validation import validate_square_matrix
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def two_opt(
    route: Sequence[int],
    mtx: Sequence[Sequence[float]],
    *,
    max_passes: int,
    fixed_start: bool = False,
    fixed_end: bool = False,
) -> tuple[list[int], float]:
    """Improve an initial route with the two opt heuristic.

    Improves heuristic routes without full brute force."""
    location = "fastest_route.core.algorithms.two_opt.two_opt"
    validate_square_matrix(mtx, location=location)
    if max_passes <= 0:
        raise ValidationError(location, "max_passes must be positive.")
    if len(route) != len(mtx):
        raise ValidationError(location, "Route length must match matrix size.")
    try:
        best = list(route)
        best_cost = sum(mtx[a][b] for a, b in zip(best, best[1:], strict=False))
        for _ in range(max_passes):
            improved = False
            first_movable = 1 if fixed_start else 0
            movable_end = len(best) - 1 if fixed_end else len(best)
            for i in range(first_movable, movable_end - 1):
                for j in range(i + 2, movable_end + 1):
                    new_route = best[:]
                    new_route[i:j] = reversed(best[i:j])
                    new_cost = sum(
                        mtx[a][b] for a, b in zip(new_route, new_route[1:], strict=False)
                    )
                    if new_cost < best_cost:
                        best, best_cost = new_route, new_cost
                        improved = True
            if not improved:
                break
        return best, best_cost
    except (IndexError, ValueError, TypeError) as exc:
        raise ValidationError(location, "Failed to compute two opt route.") from exc


def two_opt_cycle(
    route: Sequence[int],
    mtx: Sequence[Sequence[float]],
    *,
    max_passes: int,
) -> tuple[list[int], float]:
    """Improve a round-trip (cycle) route with the two opt heuristic.

    Improves greedy cycle routes without requiring exact search."""
    location = "fastest_route.core.algorithms.two_opt.two_opt_cycle"
    validate_square_matrix(mtx, location=location)
    if max_passes <= 0:
        raise ValidationError(location, "max_passes must be positive.")
    if len(route) != len(mtx):
        raise ValidationError(location, "Route length must match matrix size.")

    def cycle_cost(order: Sequence[int]) -> float:
        """Return the route cost including the closing leg."""
        legs = list(zip(order, order[1:], strict=False)) + [(order[-1], order[0])]
        return sum(mtx[a][b] for a, b in legs)

    try:
        best = list(route)
        best_cost = cycle_cost(best)
        for _ in range(max_passes):
            improved = False
            # Anchor index 0 for stable display and simpler cycle reasoning.
            for i in range(1, len(best) - 1):
                for j in range(i + 1, len(best) + 1):
                    if j - i == 1:
                        continue
                    new_route = best[:]
                    new_route[i:j] = reversed(best[i:j])
                    new_cost = cycle_cost(new_route)
                    if new_cost < best_cost:
                        best, best_cost = new_route, new_cost
                        improved = True
            if not improved:
                break
        return best, best_cost
    except (IndexError, ValueError, TypeError) as exc:
        raise ValidationError(location, "Failed to compute two opt cycle route.") from exc
