from __future__ import annotations

import pytest

from fastest_route.presentation.gui.app.workflow.guided_entry_parser import parse_guided_entry_lines
from fastest_route.presentation.gui.app.workflow.route_request_builder import build_route_request
from fastest_route.presentation.gui.app.workflow.summary_formatter import format_summary
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import (
    NON_MOTORIZED_ROUTE_WARNING,
    OptimizeFor,
    RouteKind,
    RouteRequest,
    RouteResult,
    TravelMode,
)


def test_parse_guided_entry_lines_trims_and_filters() -> None:
    """Keeps guided-entry behavior consistent across UI changes."""
    lines = parse_guided_entry_lines(raw_text="  A  \n\nB\n   C\n", min_stops=3, max_stops=10)
    assert lines == ["A", "B", "C"]


def test_parse_guided_entry_lines_enforces_min_stops() -> None:
    """Prevents users from starting workflows with insufficient inputs."""
    with pytest.raises(ValidationError):
        parse_guided_entry_lines(raw_text="A\nB\n", min_stops=3, max_stops=10)


def test_parse_guided_entry_lines_rejects_silent_truncation() -> None:
    with pytest.raises(ValidationError, match="At most 3 stops"):
        parse_guided_entry_lines(raw_text="A\nB\nC\nD\n", min_stops=2, max_stops=3)


def test_build_route_request_without_start(app_config) -> None:
    """Ensures route request construction matches UI semantics for optional starts."""
    resolved: list[str] = []

    def geocode(value: str) -> str:
        resolved.append(value)
        return f"resolved:{value}"

    request = build_route_request(
        config=app_config,
        start_raw="",
        end_raw="",
        stop_raws=[" A ", " ", "B", "C"],
        mode_value=TravelMode.DRIVING.value,
        optimize_value=OptimizeFor.TIME.value,
        trip_value=RouteKind.PATH.value,
        geocode=geocode,
        normalize=lambda s: s.strip(),
    )
    assert isinstance(request, RouteRequest)
    assert request.has_start is False
    assert request.has_end is False
    assert request.route_kind == RouteKind.PATH
    assert request.originals == ["A", "B", "C"]
    assert request.addresses == ["resolved:A", "resolved:B", "resolved:C"]
    assert resolved == ["A", "B", "C"]


def test_build_route_request_with_start(app_config) -> None:
    """Ensures request construction preserves originals while using resolved addresses for routing."""

    def geocode(value: str) -> str:
        return f"resolved:{value}"

    request = build_route_request(
        config=app_config,
        start_raw=" START ",
        end_raw="",
        stop_raws=["A", "B", "C"],
        mode_value=TravelMode.DRIVING.value,
        optimize_value=OptimizeFor.DISTANCE.value,
        trip_value=RouteKind.PATH.value,
        geocode=geocode,
        normalize=lambda s: s.strip(),
    )
    assert request.has_start is True
    assert request.has_end is False
    assert request.route_kind == RouteKind.PATH
    assert request.originals == ["START", "A", "B", "C"]
    assert request.addresses == ["resolved:START", "resolved:A", "resolved:B", "resolved:C"]
    assert request.mode == TravelMode.DRIVING
    assert request.optimize_for == OptimizeFor.DISTANCE


def test_build_route_request_with_fixed_end(app_config) -> None:
    """Fixed end is a common routing workflow and must be represented explicitly in the request."""

    def geocode(value: str) -> str:
        return f"resolved:{value}"

    request = build_route_request(
        config=app_config,
        start_raw="",
        end_raw=" END ",
        stop_raws=["A", "B", "C"],
        mode_value=TravelMode.DRIVING.value,
        optimize_value=OptimizeFor.TIME.value,
        trip_value=RouteKind.PATH.value,
        geocode=geocode,
        normalize=lambda s: s.strip(),
    )
    assert request.has_start is False
    assert request.has_end is True
    assert request.route_kind == RouteKind.PATH
    assert request.originals[-1] == "END"
    assert request.addresses[-1] == "resolved:END"


def test_build_route_request_round_trip_rejects_fixed_end(app_config) -> None:
    """Reject a contradictory fixed end without making geocoding calls."""

    geocoded: list[str] = []

    def geocode(value: str) -> str:
        geocoded.append(value)
        return f"resolved:{value}"

    with pytest.raises(ValidationError):
        build_route_request(
            config=app_config,
            start_raw="",
            end_raw="END",
            stop_raws=["A", "B", "C"],
            mode_value=TravelMode.DRIVING.value,
            optimize_value=OptimizeFor.TIME.value,
            trip_value=RouteKind.ROUND_TRIP.value,
            geocode=geocode,
            normalize=lambda s: s.strip(),
        )
    assert geocoded == []


def test_format_summary_includes_metric_and_link() -> None:
    """Ensures output strings remain stable for users and debugging."""
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = RouteResult(order=[0, 1, 2], total=12.0, units="min", legs=[5.0, 7.0])
    summary = format_summary(
        request=request, result=result, route_lines="0\n1\n2", route_link="http://example"
    )
    assert "Total estimated time" in summary
    assert "Leg breakdown" in summary
    assert "http://example" in summary


@pytest.mark.parametrize("mode", [TravelMode.WALKING, TravelMode.BICYCLING])
def test_format_summary_always_displays_non_motorized_safety_warning(mode: TravelMode) -> None:
    """The final presentation boundary enforces the required caution for both modes."""
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=mode,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = RouteResult(
        order=[0, 1, 2],
        total=12.0,
        units="min",
        legs=[5.0, 7.0],
        warnings=("Provider-specific warning.",),
    )

    summary = format_summary(
        request=request,
        result=result,
        route_lines="0\n1\n2",
        route_link="https://www.google.com/maps/dir/",
    )

    assert "Safety warning:" in summary
    assert NON_MOTORIZED_ROUTE_WARNING in summary
    assert "Provider-specific warning." in summary
