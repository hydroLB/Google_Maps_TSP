"""Core route orchestration over matrix and cache ports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.core.algorithms.solver import TspSolver
from fastest_route.observability.logger import get_logger
from fastest_route.shared.errors import ExternalServiceError, ValidationError
from fastest_route.shared.types import OptimizeFor, RouteKind, RouteResult, route_safety_warnings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastest_route.config.registry import AppConfig
    from fastest_route.core.ports import RouteCachePort, RouteMatrixPort
    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import RouteRequest

logger = get_logger(__name__, component="routing_service")


class RoutingService:
    """Coordinate route computation through core-owned dependency ports."""

    def __init__(
        self,
        *,
        config: AppConfig,
        maps_client: RouteMatrixPort,
        cache_store: RouteCachePort,
    ) -> None:
        """Initialize routing with matrix and cache port implementations."""
        location = "fastest_route.core.routing.routing_service.RoutingService.__init__"
        try:
            if not config:
                raise ValidationError(location, "Config is required.")
            self._config = config
            self._maps_client = maps_client
            self._cache_store = cache_store
            self._solver = TspSolver(config.routing)
        except ValidationError:
            raise
        except AttributeError as exc:
            raise ValidationError(location, "RoutingService dependencies are invalid.") from exc

    def compute_route(
        self,
        request: RouteRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> RouteResult:
        """Compute an optimized route from request inputs.

        Centralizes route computation with caching and validation."""
        location = "fastest_route.core.routing.routing_service.RoutingService.compute_route"
        try:
            if not request.addresses:
                raise ValidationError(location, "At least one address is required.")
            if len(request.originals) != len(request.addresses):
                raise ValidationError(location, "Original and resolved address counts must match.")
            if not isinstance(request.has_start, bool) or not isinstance(request.has_end, bool):
                raise ValidationError(location, "Endpoint flags must be boolean values.")
            if request.route_kind == RouteKind.ROUND_TRIP and request.has_end:
                raise ValidationError(location, "Round trips do not support a fixed end address.")

            endpoint_count = int(request.has_start) + int(request.has_end)
            if endpoint_count > len(request.addresses):
                raise ValidationError(
                    location, "Endpoint flags are incompatible with the address list."
                )
            stop_count = len(request.addresses) - endpoint_count
            if stop_count < self._config.ui.min_stops:
                raise ValidationError(location, "Not enough stops to compute a route.")
            if stop_count > self._config.ui.max_stops:
                raise ValidationError(location, "Too many stops for the configured limits.")

            cached = self._cache_store.get_cached_route(
                request.addresses,
                request.mode.value,
                request.optimize_for.value,
                request.has_start,
                request.has_end,
                request.route_kind.value,
                self._maps_client.get_route_cache_key(
                    mode=request.mode, metric=request.optimize_for
                ),
            )
            if cached:
                order, total, legs = cached
                return RouteResult(
                    order=order,
                    total=total,
                    units=self._units(request.optimize_for),
                    legs=legs,
                    warnings=route_safety_warnings(request.mode),
                )

            matrix = self._maps_client.build_matrix(
                request.addresses,
                request.mode,
                request.optimize_for,
                cancellation_token=cancellation_token,
                max_seconds=self._config.routing.max_compute_seconds,
            )
            start_index = 0 if request.has_start else None
            end_index = len(matrix) - 1 if request.has_end else None
            order, total = self._solver.solve(
                matrix,
                start_index=start_index,
                end_index=end_index,
                route_kind=request.route_kind,
            )

            legs = self._compute_legs(
                matrix,
                order=order,
                is_round_trip=request.route_kind == RouteKind.ROUND_TRIP,
            )
            total = sum(legs)
            self._cache_store.cache_route(
                request.addresses,
                request.mode.value,
                request.optimize_for.value,
                request.has_start,
                request.has_end,
                request.route_kind.value,
                self._maps_client.get_route_cache_key(
                    mode=request.mode, metric=request.optimize_for
                ),
                order,
                total,
                legs,
            )
            return RouteResult(
                order=order,
                total=total,
                units=self._units(request.optimize_for),
                legs=legs,
                warnings=route_safety_warnings(request.mode),
            )
        except ValidationError:
            raise
        except ExternalServiceError as exc:
            raise ExternalServiceError(location, f"Routing failed. {exc}") from exc
        except (AttributeError, TypeError) as exc:
            raise ValidationError(location, "Routing failed due to invalid inputs.") from exc

    def _solve_with_fixed_start(self, matrix: Sequence[Sequence[float]]) -> tuple[list[int], float]:
        """Solve a TSP matrix while fixing the first node as start.

        Ensures start node remains fixed in the final route."""
        location = (
            "fastest_route.core.routing.routing_service.RoutingService._solve_with_fixed_start"
        )
        if len(matrix) < 2:
            raise ValidationError(location, "Matrix must have at least two nodes.")
        try:
            sub_matrix = [row[1:] for row in matrix[1:]]
            sub_order, total = self._solver.solve(sub_matrix)
            order = [0] + [index + 1 for index in sub_order]
            return order, total
        except ValidationError:
            raise
        except ExternalServiceError as exc:
            raise ExternalServiceError(location, "Failed to solve route with fixed start.") from exc
        except (IndexError, TypeError) as exc:
            raise ValidationError(location, "Failed to solve route with fixed start.") from exc

    def _units(self, optimize_for: OptimizeFor) -> str:
        """Return units label based on optimization metric.

        Keeps units consistent across outputs."""
        location = "fastest_route.core.routing.routing_service.RoutingService._units"
        try:
            if optimize_for == OptimizeFor.TIME:
                return "min"
            if optimize_for == OptimizeFor.DISTANCE:
                return "km"
            raise ValidationError(location, "Unsupported optimize_for value.")
        except ValidationError:
            raise
        except (AttributeError, TypeError) as exc:
            raise ValidationError(location, "Unsupported optimize_for value.") from exc

    def _compute_legs(
        self,
        matrix: Sequence[Sequence[float]],
        *,
        order: Sequence[int],
        is_round_trip: bool,
    ) -> list[float]:
        """Compute per-leg values for a route order using the distance matrix.

        Preserves the exact per-leg values used to compute totals without requiring re-querying providers."""
        location = "fastest_route.core.routing.routing_service.RoutingService._compute_legs"
        if not order:
            raise ValidationError(location, "order must not be empty.")
        try:
            legs: list[float] = []
            for a, b in zip(order, order[1:], strict=False):
                legs.append(float(matrix[a][b]))
            if is_round_trip:
                legs.append(float(matrix[order[-1]][order[0]]))
            return legs
        except (IndexError, TypeError, ValueError) as exc:
            raise ValidationError(location, "Failed to compute per-leg values.") from exc
