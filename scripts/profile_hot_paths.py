"""Profile TSP solver hot paths with a repeatable, evidence-based harness."""

from __future__ import annotations

import cProfile
import pstats
from pathlib import Path

from fastest_route.config.registry import RoutingConfig
from fastest_route.core.algorithms.solver import TspSolver
from fastest_route.shared.types import OptimizeFor, TravelMode


def main() -> None:
    """Profile the solver with a synthetic matrix, avoiding live API calls."""
    location = "scripts.profile_hot_paths.main"
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
        max_compute_seconds=10.0,
    )
    solver = TspSolver(config)
    profiler = cProfile.Profile()
    profiler.enable()
    solver.solve(matrix)
    profiler.disable()

    try:
        output_dir = Path("profiles")
        output_dir.mkdir(parents=True, exist_ok=True)
        profile_path = output_dir / "hot_paths.prof"
        text_path = output_dir / "hot_paths.txt"
        profiler.dump_stats(profile_path)
        with text_path.open("w", encoding="utf-8") as handle:
            stats = pstats.Stats(profiler, stream=handle).sort_stats("cumulative")
            stats.print_stats(20)
    except OSError as exc:
        raise RuntimeError(f"{location}: Failed to write profiling output.") from exc


if __name__ == "__main__":
    main()
