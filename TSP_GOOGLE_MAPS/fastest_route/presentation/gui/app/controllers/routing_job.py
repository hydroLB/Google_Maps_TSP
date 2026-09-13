"""Routing job composition helpers for the GUI."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import TYPE_CHECKING

from fastest_route.observability.metrics import (
    increment_counter,
    observe_duration_seconds,
)
from fastest_route.presentation.gui.app.workflow.summary_formatter import format_summary
from fastest_route.shared.utils.address_utils import build_route_link, generate_route_lines

if TYPE_CHECKING:
    from fastest_route.core.routing.routing_service import RoutingService
    from fastest_route.shared.cancellation import CancellationToken
    from fastest_route.shared.types import RouteRequest, RouteResult


def compute_route_artifacts(
    *,
    routing_service: RoutingService,
    request: RouteRequest,
    cancellation_token: CancellationToken,
) -> tuple[str, str, RouteResult]:
    """Compute a route and derive UI artifacts (link and summary) from the result."""
    tags = {
        "mode": request.mode.value,
        "optimize_for": request.optimize_for.value,
        "route_kind": request.route_kind.value,
    }
    start = time.monotonic()
    try:
        with suppress(Exception):
            increment_counter("routing.requests_total", tags=tags)
        result = routing_service.compute_route(request, cancellation_token=cancellation_token)
        route_link = build_route_link(
            request.addresses,
            result.order,
            request.mode,
            has_start=request.has_start,
            has_end=request.has_end,
            route_kind=request.route_kind.value,
            start_resolved=request.addresses[0] if request.has_start else None,
            end_resolved=request.addresses[-1] if request.has_end else None,
        )
        route_lines = generate_route_lines(
            result.order,
            request.addresses,
            request.originals,
            request.has_start,
            request.has_end,
            request.route_kind.value,
        )
        summary = format_summary(
            request=request, result=result, route_lines=route_lines, route_link=route_link
        )
        with suppress(Exception):
            increment_counter("routing.success_total", tags=tags)
        return route_link, summary, result
    except Exception:
        with suppress(Exception):
            increment_counter("routing.failure_total", tags=tags)
        raise
    finally:
        elapsed = max(0.0, time.monotonic() - start)
        with suppress(Exception):
            observe_duration_seconds("routing.compute_duration_seconds", value=elapsed, tags=tags)
