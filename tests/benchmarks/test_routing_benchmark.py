from __future__ import annotations

import pytest

from fastest_route.config.registry import RoutingConfig
from fastest_route.core.algorithms.solver import TspSolver
from fastest_route.shared.types import OptimizeFor, TravelMode


@pytest.mark.benchmark
def test_tsp_solver_benchmark(benchmark) -> None:
    matrix = [
        [0.0, 2.0, 9.0, 10.0, 7.0, 3.0, 8.0, 5.0],
        [2.0, 0.0, 6.0, 4.0, 3.0, 8.0, 5.0, 7.0],
        [9.0, 6.0, 0.0, 8.0, 2.0, 5.0, 6.0, 4.0],
        [10.0, 4.0, 8.0, 0.0, 6.0, 9.0, 3.0, 2.0],
        [7.0, 3.0, 2.0, 6.0, 0.0, 4.0, 5.0, 8.0],
        [3.0, 8.0, 5.0, 9.0, 4.0, 0.0, 7.0, 6.0],
        [8.0, 5.0, 6.0, 3.0, 5.0, 7.0, 0.0, 9.0],
        [5.0, 7.0, 4.0, 2.0, 8.0, 6.0, 9.0, 0.0],
    ]
    config = RoutingConfig(
        max_exact=6,
        two_opt_max_passes=6,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    solver = TspSolver(config)
    benchmark.pedantic(solver.solve, args=(matrix,), rounds=50, iterations=200)
