"""Strategy selector for solving TSP matrices.

Encapsulates algorithm selection and tuning in one place."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.core.algorithms.brute_force import brute_force_cycle, brute_force_path
from fastest_route.core.algorithms.nearest_neighbor import (
    nearest_neighbor,
    nearest_neighbor_with_fixed_end,
)
from fastest_route.core.algorithms.two_opt import two_opt, two_opt_cycle
from fastest_route.core.algorithms.validation import validate_square_matrix
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import RouteKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.config.registry import RoutingConfig


class TspSolver:
    """Solve the traveling salesperson problem using configured algorithms.

    Centralizes algorithm selection and tuning logic."""

    def __init__(self, config: RoutingConfig) -> None:
        """Initialize the solver with routing configuration.

        Keeps solver behavior aligned with config."""
        location = "fastest_route.core.algorithms.solver.TspSolver.__init__"
        try:
            if config.max_exact <= 1:
                raise ValidationError(location, "max_exact must be greater than 1.")
            self._config = config
        except AttributeError as exc:
            raise ValidationError(location, "config must be a RoutingConfig.") from exc

    def solve(
        self,
        mtx: Sequence[Sequence[float]],
        *,
        start_index: int | None = None,
        end_index: int | None = None,
        route_kind: RouteKind = RouteKind.PATH,
    ) -> tuple[list[int], float]:
        """Solve a TSP matrix with the configured strategy and route constraints.

        Provides a single entry point for TSP solving across common route shapes."""
        location = "fastest_route.core.algorithms.solver.TspSolver.solve"
        validate_square_matrix(mtx, location=location)
        try:
            n = len(mtx)
            if start_index is not None and (start_index < 0 or start_index >= n):
                raise ValidationError(location, "start_index is out of range.")
            if end_index is not None and (end_index < 0 or end_index >= n):
                raise ValidationError(location, "end_index is out of range.")
            if start_index is not None and end_index is not None and start_index == end_index:
                raise ValidationError(location, "start_index and end_index must not be the same.")
            if not isinstance(route_kind, RouteKind):
                raise ValidationError(location, "route_kind must be a RouteKind.")

            fixed_endpoints = int(start_index is not None) + int(end_index is not None)
            variable_nodes = n - fixed_endpoints

            if route_kind == RouteKind.ROUND_TRIP:
                if end_index is not None:
                    raise ValidationError(location, "end_index is not supported for round trips.")
                variable_nodes = n - 1 if start_index is not None else n
                if variable_nodes <= self._config.max_exact:
                    return brute_force_cycle(mtx, start_index=start_index)
                start = start_index if start_index is not None else 0
                route = nearest_neighbor(mtx, start_index=start)
                return two_opt_cycle(route, mtx, max_passes=self._config.two_opt_max_passes)

            if variable_nodes <= self._config.max_exact:
                return brute_force_path(mtx, start_index=start_index, end_index=end_index)

            if start_index is not None and end_index is not None:
                route = nearest_neighbor_with_fixed_end(
                    mtx, start_index=start_index, end_index=end_index
                )
                return two_opt(
                    route,
                    mtx,
                    max_passes=self._config.two_opt_max_passes,
                    fixed_start=True,
                    fixed_end=True,
                )

            if end_index is not None and start_index is None:
                start = self._config.nearest_neighbor_start_index
                if start < 0 or start >= n:
                    raise ValidationError(
                        location,
                        "nearest_neighbor_start_index is out of range for this matrix.",
                    )
                if start == end_index:
                    start = 0 if end_index != 0 else 1
                route = nearest_neighbor_with_fixed_end(mtx, start_index=start, end_index=end_index)
                return two_opt(
                    route,
                    mtx,
                    max_passes=self._config.two_opt_max_passes,
                    fixed_end=True,
                )

            start = (
                start_index
                if start_index is not None
                else self._config.nearest_neighbor_start_index
            )
            if start < 0 or start >= n:
                raise ValidationError(
                    location,
                    "nearest_neighbor_start_index is out of range for this matrix.",
                )
            route = nearest_neighbor(mtx, start_index=start)
            return two_opt(
                route,
                mtx,
                max_passes=self._config.two_opt_max_passes,
                fixed_start=start_index is not None,
            )
        except ValidationError as exc:
            raise ValidationError(location, f"Failed to solve matrix. {exc}") from exc
        except (IndexError, TypeError, ValueError) as exc:
            raise ValidationError(location, "Failed to solve matrix due to invalid data.") from exc
