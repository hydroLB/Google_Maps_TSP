from __future__ import annotations

import builtins
import itertools

import pytest

from fastest_route.config.loader import get_config
from fastest_route.config.registry import RoutingConfig
from fastest_route.core.algorithms.brute_force import (
    brute_force_cycle,
    brute_force_path,
)
from fastest_route.core.algorithms.nearest_neighbor import (
    nearest_neighbor,
    nearest_neighbor_with_fixed_end,
)
from fastest_route.core.algorithms.solver import TspSolver
from fastest_route.core.algorithms.two_opt import two_opt, two_opt_cycle
from fastest_route.core.algorithms.validation import validate_square_matrix
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import OptimizeFor, RouteKind, TravelMode


def test_brute_force_path_finds_min_cost() -> None:
    matrix = [
        [0.0, 1.0, 2.0],
        [1.0, 0.0, 3.0],
        [2.0, 3.0, 0.0],
    ]
    order, cost = brute_force_path(matrix)
    assert len(order) == 3
    assert cost == 3.0


def test_nearest_neighbor_respects_start_index() -> None:
    matrix = [
        [0.0, 5.0, 9.0],
        [5.0, 0.0, 1.0],
        [9.0, 1.0, 0.0],
    ]
    route = nearest_neighbor(matrix, start_index=1)
    assert route[0] == 1
    assert set(route) == {0, 1, 2}


def test_two_opt_improves_or_equals_cost() -> None:
    matrix = [
        [0.0, 5.0, 9.0],
        [5.0, 0.0, 1.0],
        [9.0, 1.0, 0.0],
    ]
    initial_route = [0, 2, 1]
    _, initial_cost = two_opt(initial_route, matrix, max_passes=1)
    optimized_route, optimized_cost = two_opt(initial_route, matrix, max_passes=5)
    assert set(optimized_route) == {0, 1, 2}
    assert optimized_cost <= initial_cost


def test_tsp_solver_uses_brute_force_for_small_matrices() -> None:
    matrix = [
        [0.0, 5.0, 9.0],
        [5.0, 0.0, 1.0],
        [9.0, 1.0, 0.0],
    ]
    config = RoutingConfig(
        max_exact=5,
        two_opt_max_passes=5,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    solver = TspSolver(config)
    _, cost = solver.solve(matrix)
    assert cost == 6.0


def test_validate_square_matrix_rejects_invalid_input() -> None:
    invalid_matrix = [[0.0, 1.0], [1.0]]
    with pytest.raises(ValidationError):
        validate_square_matrix(invalid_matrix, location="test")


def test_validate_square_matrix_rejects_empty_matrix() -> None:
    with pytest.raises(ValidationError):
        validate_square_matrix([], location="test")


def test_validate_square_matrix_rejects_non_numeric_values() -> None:
    with pytest.raises(ValidationError):
        validate_square_matrix([[0.0, "bad"], [1.0, 0.0]], location="test")


@pytest.mark.parametrize(
    ("invalid_value", "message"),
    [
        (True, "must not be a boolean"),
        (float("nan"), "must be finite"),
        (float("inf"), "must be finite"),
        (float("-inf"), "must be finite"),
        (-1.0, "must be zero or greater"),
    ],
)
def test_validate_square_matrix_rejects_invalid_numeric_costs(
    invalid_value: float | bool,
    message: str,
) -> None:
    """Reject values that cannot represent valid route costs."""
    matrix = [[0.0, invalid_value], [1.0, 0.0]]

    with pytest.raises(ValidationError, match=message):
        validate_square_matrix(matrix, location="test")


def test_tsp_solver_uses_loaded_config(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = [
        [0.0, 1.0, 2.0],
        [1.0, 0.0, 3.0],
        [2.0, 3.0, 0.0],
    ]
    monkeypatch.setenv("FASTEST_ROUTE_ENV", "test")
    get_config.cache_clear()
    solver = TspSolver(get_config().routing)
    order, cost = solver.solve(matrix)
    assert len(order) == 3
    assert cost == 3.0


def test_brute_force_wraps_internal_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = [
        [0.0, 1.0],
        [1.0, 0.0],
    ]
    monkeypatch.setattr(
        itertools, "permutations", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom"))
    )
    with pytest.raises(ValidationError):
        brute_force_path(matrix)


def test_nearest_neighbor_invalid_start_index() -> None:
    matrix = [
        [0.0, 1.0],
        [1.0, 0.0],
    ]
    with pytest.raises(ValidationError):
        nearest_neighbor(matrix, start_index=5)


def test_nearest_neighbor_wraps_internal_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = [
        [0.0, 1.0],
        [1.0, 0.0],
    ]
    monkeypatch.setattr(
        builtins,
        "min",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    with pytest.raises(ValidationError):
        nearest_neighbor(matrix, start_index=0)


def test_two_opt_rejects_invalid_inputs() -> None:
    matrix = [
        [0.0, 1.0],
        [1.0, 0.0],
    ]
    with pytest.raises(ValidationError):
        two_opt([0, 1], matrix, max_passes=0)
    with pytest.raises(ValidationError):
        two_opt([0], matrix, max_passes=1)


def test_two_opt_can_swap_two_interiors_between_fixed_endpoints() -> None:
    """Two movable interior nodes are enough for a useful two-opt swap."""
    matrix = [
        [0.0, 10.0, 1.0, 10.0],
        [10.0, 0.0, 1.0, 1.0],
        [1.0, 1.0, 0.0, 10.0],
        [10.0, 1.0, 10.0, 0.0],
    ]

    route, cost = two_opt(
        [0, 1, 2, 3],
        matrix,
        max_passes=2,
        fixed_start=True,
        fixed_end=True,
    )

    assert route == [0, 2, 1, 3]
    assert cost == 3.0


def test_two_opt_only_preserves_requested_endpoint() -> None:
    """A free path endpoint remains movable during refinement."""
    end_fixed_matrix = [
        [0.0, 1.0, 2.0, 9.0],
        [1.0, 0.0, 10.0, 9.0],
        [9.0, 9.0, 0.0, 1.0],
        [9.0, 9.0, 9.0, 0.0],
    ]
    start_fixed_matrix = [
        [0.0, 1.0, 9.0, 9.0],
        [9.0, 0.0, 1.0, 2.0],
        [9.0, 9.0, 0.0, 10.0],
        [9.0, 9.0, 1.0, 0.0],
    ]

    end_fixed_route, _ = two_opt([0, 1, 2, 3], end_fixed_matrix, max_passes=2, fixed_end=True)
    start_fixed_route, _ = two_opt([0, 1, 2, 3], start_fixed_matrix, max_passes=2, fixed_start=True)

    assert end_fixed_route[0] != 0
    assert end_fixed_route[-1] == 3
    assert start_fixed_route[0] == 0
    assert start_fixed_route[-1] != 3


def test_two_opt_wraps_internal_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = [
        [0.0, 1.0],
        [1.0, 0.0],
    ]
    monkeypatch.setattr(
        builtins,
        "sum",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    with pytest.raises(ValidationError):
        two_opt([0, 1], matrix, max_passes=1)


def test_validate_square_matrix_rejects_missing_location() -> None:
    with pytest.raises(ValidationError):
        validate_square_matrix([[0.0]], location="")


def test_validate_square_matrix_rejects_non_sequence_rows() -> None:
    with pytest.raises(ValidationError):
        validate_square_matrix([1, 2], location="test")


def test_validate_square_matrix_rejects_non_sequence_matrix() -> None:
    with pytest.raises(ValidationError):
        validate_square_matrix(5, location="test")


def test_tsp_solver_rejects_invalid_config() -> None:
    config = RoutingConfig(
        max_exact=1,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    with pytest.raises(ValidationError):
        TspSolver(config)


def test_tsp_solver_rejects_invalid_config_type() -> None:
    with pytest.raises(ValidationError):
        TspSolver(object())


def test_tsp_solver_wraps_validation_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    config = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    solver = TspSolver(config)
    monkeypatch.setattr(
        "fastest_route.core.algorithms.solver.nearest_neighbor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("test", "boom")),
    )
    with pytest.raises(ValidationError):
        solver.solve([[0.0, 1.0, 2.0], [1.0, 0.0, 3.0], [2.0, 3.0, 0.0]])


def test_tsp_solver_wraps_type_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    config = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    solver = TspSolver(config)
    monkeypatch.setattr(
        "fastest_route.core.algorithms.solver.two_opt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("boom")),
    )
    with pytest.raises(ValidationError):
        solver.solve([[0.0, 1.0, 2.0], [1.0, 0.0, 3.0], [2.0, 3.0, 0.0]])


def test_brute_force_path_respects_fixed_start_and_end() -> None:
    matrix = [
        [0.0, 1.0, 10.0, 10.0],
        [1.0, 0.0, 1.0, 10.0],
        [10.0, 1.0, 0.0, 1.0],
        [10.0, 10.0, 1.0, 0.0],
    ]
    order, cost = brute_force_path(matrix, start_index=0, end_index=3)
    assert order[0] == 0
    assert order[-1] == 3
    assert set(order) == {0, 1, 2, 3}
    assert cost == 3.0


def test_brute_force_cycle_includes_return_leg() -> None:
    matrix = [
        [0.0, 1.0, 5.0],
        [1.0, 0.0, 1.0],
        [5.0, 1.0, 0.0],
    ]
    order, cost = brute_force_cycle(matrix, start_index=1)
    assert order[0] == 1
    assert set(order) == {0, 1, 2}
    legs = list(zip(order, order[1:], strict=False)) + [(order[-1], order[0])]
    assert cost == sum(matrix[a][b] for a, b in legs)


def test_nearest_neighbor_with_fixed_end_respects_end() -> None:
    matrix = [
        [0.0, 1.0, 2.0, 3.0],
        [1.0, 0.0, 1.0, 2.0],
        [2.0, 1.0, 0.0, 1.0],
        [3.0, 2.0, 1.0, 0.0],
    ]
    route = nearest_neighbor_with_fixed_end(matrix, start_index=0, end_index=3)
    assert route[0] == 0
    assert route[-1] == 3
    assert set(route) == {0, 1, 2, 3}


def test_two_opt_cycle_cost_matches_route() -> None:
    matrix = [
        [0.0, 2.0, 9.0, 10.0],
        [2.0, 0.0, 6.0, 4.0],
        [9.0, 6.0, 0.0, 8.0],
        [10.0, 4.0, 8.0, 0.0],
    ]
    route, cost = two_opt_cycle([0, 2, 1, 3], matrix, max_passes=3)
    legs = list(zip(route, route[1:], strict=False)) + [(route[-1], route[0])]
    assert cost == sum(matrix[a][b] for a, b in legs)


def test_tsp_solver_heuristic_fixed_end_preserves_end() -> None:
    matrix = [
        [0.0, 1.0, 5.0, 5.0, 9.0],
        [1.0, 0.0, 1.0, 5.0, 5.0],
        [5.0, 1.0, 0.0, 1.0, 5.0],
        [5.0, 5.0, 1.0, 0.0, 1.0],
        [9.0, 5.0, 5.0, 1.0, 0.0],
    ]
    cfg = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    solver = TspSolver(cfg)
    order, _total = solver.solve(matrix, end_index=4, route_kind=RouteKind.PATH)
    assert order[-1] == 4
    assert set(order) == {0, 1, 2, 3, 4}


def test_tsp_solver_end_only_constraint_does_not_fix_configured_start() -> None:
    """The configured greedy seed is not a route constraint."""
    matrix = [
        [0.0, 1.0, 2.0, 9.0],
        [1.0, 0.0, 10.0, 9.0],
        [9.0, 9.0, 0.0, 1.0],
        [9.0, 9.0, 9.0, 0.0],
    ]
    cfg = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )

    order, total = TspSolver(cfg).solve(matrix, end_index=3)

    assert order == [1, 0, 2, 3]
    assert total == 4.0


def test_tsp_solver_start_only_constraint_does_not_fix_route_end() -> None:
    """A fixed start does not turn the greedy route end into a constraint."""
    matrix = [
        [0.0, 1.0, 9.0, 9.0],
        [9.0, 0.0, 1.0, 2.0],
        [9.0, 9.0, 0.0, 10.0],
        [9.0, 9.0, 1.0, 0.0],
    ]
    cfg = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )

    order, total = TspSolver(cfg).solve(matrix, start_index=0)

    assert order == [0, 1, 3, 2]
    assert total == 4.0


def test_tsp_solver_unconstrained_path_can_move_both_greedy_endpoints() -> None:
    """Greedy seed endpoints remain movable on an unconstrained path."""
    start_moving_matrix = [
        [0.0, 1.0, 2.0, 9.0],
        [1.0, 0.0, 10.0, 9.0],
        [9.0, 9.0, 0.0, 1.0],
        [9.0, 9.0, 9.0, 0.0],
    ]
    end_moving_matrix = [
        [0.0, 1.0, 9.0, 9.0],
        [9.0, 0.0, 1.0, 2.0],
        [9.0, 9.0, 0.0, 10.0],
        [9.0, 9.0, 1.0, 0.0],
    ]
    cfg = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )

    start_moved, _ = TspSolver(cfg).solve(start_moving_matrix)
    end_moved, _ = TspSolver(cfg).solve(end_moving_matrix)

    assert start_moved[0] != 0
    assert end_moved[-1] != 3


def test_tsp_solver_rejects_configured_start_outside_current_matrix() -> None:
    """A globally valid configured seed must also fit the current route size."""
    matrix = [
        [0.0, 1.0, 2.0],
        [1.0, 0.0, 1.0],
        [2.0, 1.0, 0.0],
    ]
    cfg = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=3,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )

    with pytest.raises(ValidationError, match="nearest_neighbor_start_index is out of range"):
        TspSolver(cfg).solve(matrix)


def test_tsp_solver_heuristic_round_trip_includes_return_leg() -> None:
    matrix = [
        [0.0, 1.0, 5.0, 5.0],
        [1.0, 0.0, 1.0, 5.0],
        [5.0, 1.0, 0.0, 1.0],
        [5.0, 5.0, 1.0, 0.0],
    ]
    cfg = RoutingConfig(
        max_exact=2,
        two_opt_max_passes=2,
        nearest_neighbor_start_index=0,
        default_mode=TravelMode.DRIVING,
        default_optimize_for=OptimizeFor.TIME,
        max_compute_seconds=5.0,
    )
    solver = TspSolver(cfg)
    order, total = solver.solve(matrix, route_kind=RouteKind.ROUND_TRIP)
    legs = list(zip(order, order[1:], strict=False)) + [(order[-1], order[0])]
    assert total == sum(matrix[a][b] for a, b in legs)
