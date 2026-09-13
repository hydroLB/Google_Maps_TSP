"""Format a RouteRequest and RouteResult into a display string."""

from __future__ import annotations

from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import (
    OptimizeFor,
    RouteKind,
    RouteRequest,
    RouteResult,
    route_safety_warnings,
)


def _format_leg_breakdown(*, request: RouteRequest, result: RouteResult) -> str:
    """Format a per-leg breakdown with cumulative totals for UI display."""
    location = "fastest_route.presentation.gui.app.workflow.summary_formatter._format_leg_breakdown"
    try:
        if not result.order:
            raise ValidationError(location, "Route order must not be empty.")
        if not result.legs:
            raise ValidationError(location, "Route legs must not be empty.")
        ordered_addrs = [request.addresses[idx] for idx in result.order]
        ordered_origs = [request.originals[idx] for idx in result.order]
        if request.route_kind == RouteKind.ROUND_TRIP:
            expected = len(result.order)
            if len(result.legs) != expected:
                raise ValidationError(location, "Round trip leg count mismatch.")
        else:
            expected = max(len(result.order) - 1, 0)
            if len(result.legs) != expected:
                raise ValidationError(location, "One-way leg count mismatch.")

        def fmt(value: float) -> str:
            """Execute `fmt`."""
            if request.optimize_for == OptimizeFor.DISTANCE:
                return f"{value:.2f}"
            return f"{value:.0f}"

        lines: list[str] = []
        cumulative = 0.0
        pairs = list(zip(result.order, result.order[1:], strict=False))
        for idx, ((a, b), value) in enumerate(
            zip(pairs, result.legs[: len(pairs)], strict=False), start=1
        ):
            cumulative += float(value)
            lines.append(
                f"{idx}. {request.addresses[a]} -> {request.addresses[b]}: {fmt(float(value))} {result.units} "
                f"(cum {fmt(cumulative)} {result.units})"
            )
        if request.route_kind == RouteKind.ROUND_TRIP:
            value = float(result.legs[-1])
            cumulative += value
            lines.append(
                f"Return. {ordered_addrs[-1]} -> {ordered_addrs[0]}: {fmt(value)} {result.units} "
                f"(cum {fmt(cumulative)} {result.units})"
            )
        if request.has_start:
            lines.insert(
                0,
                f"Start: {ordered_addrs[0]} (your input: {ordered_origs[0]})",
            )
        if request.has_end:
            lines.append(
                f"End: {ordered_addrs[-1]} (your input: {ordered_origs[-1]})",
            )
        return "Leg breakdown:\n" + "\n".join(lines)
    except ValidationError:
        raise
    except (IndexError, TypeError, ValueError) as exc:
        raise ValidationError(location, "Failed to format leg breakdown.") from exc


def format_summary(
    *, request: RouteRequest, result: RouteResult, route_lines: str, route_link: str
) -> str:
    """Build the summary string for the output panel."""
    location = "fastest_route.presentation.gui.app.workflow.summary_formatter.format_summary"
    try:
        trip_label = "Round trip" if request.route_kind == RouteKind.ROUND_TRIP else "One-way"
        metric_line = (
            f"Total route distance: {result.total:.2f} {result.units}"
            if request.optimize_for == OptimizeFor.DISTANCE
            else f"Total estimated time: {result.total:.0f} {result.units}"
        )
        order_label = (
            "Shortest order" if request.optimize_for == OptimizeFor.DISTANCE else "Fastest order"
        )
        legs = _format_leg_breakdown(request=request, result=result)
        warnings = tuple(dict.fromkeys((*route_safety_warnings(request.mode), *result.warnings)))
        warning_block = ""
        if warnings:
            warning_block = "\n\nSafety warning:\n" + "\n".join(
                f"- {warning}" for warning in warnings
            )
        return (
            f"Trip: {trip_label}\n"
            f"Travel mode: {request.mode.value.title()}\n"
            f"{metric_line}\n\n"
            f"{order_label} (resolved address shown, original input in parentheses):\n"
            f"{route_lines}\n\n{legs}{warning_block}\n\n{route_link}"
        )
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError(location, "Failed to format summary.") from exc
