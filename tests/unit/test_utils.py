from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import pytest

from fastest_route.infrastructure.cache.keys import build_distance_key
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import RouteKind, TravelMode
from fastest_route.shared.utils.links import build_maps_link, build_route_link
from fastest_route.shared.utils.normalization import normalize_address_input
from fastest_route.shared.utils.presenters import generate_route_lines


def test_normalize_address_input_extracts_place_name() -> None:
    url = "https://www.google.com/maps/place/Some+Place/@37.0,-122.0,15z"
    assert normalize_address_input(url) == "Some Place"


def test_normalize_address_input_keeps_coordinates() -> None:
    coords = "37.1234, -122.5678"
    with pytest.raises(ValidationError, match=re.escape("Coordinates are not supported.")):
        normalize_address_input(coords)


def test_normalize_address_input_extracts_coordinates_from_url() -> None:
    url = "https://www.google.com/maps/@37.1111,-122.2222,15z"
    with pytest.raises(
        ValidationError,
        match=re.escape("Google Maps links that contain only coordinates are not supported."),
    ):
        normalize_address_input(url)


def test_normalize_address_input_extracts_origin_from_url() -> None:
    url = "https://www.google.com/maps/dir/?api=1&origin=Main%20St"
    assert normalize_address_input(url) == "Main St"


def test_normalize_address_input_extracts_pin_coordinates() -> None:
    url = "https://www.google.com/maps/place/37.9,-122.9"
    with pytest.raises(
        ValidationError,
        match=re.escape("Google Maps links pointing only to coordinates are not supported."),
    ):
        normalize_address_input(url)


def test_normalize_address_input_cleans_whitespace() -> None:
    text = "  Main   Street  "
    assert normalize_address_input(text) == "Main Street"


def test_normalize_address_input_rejects_non_string() -> None:
    with pytest.raises(ValidationError):
        normalize_address_input(123)


def test_normalize_address_input_handles_regex_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fastest_route.shared.utils.normalization.re.search",
        lambda *args, **kwargs: (_ for _ in ()).throw(re.error("boom")),
    )
    with pytest.raises(ValidationError):
        normalize_address_input("https://google.com/maps/place/test")


def test_build_route_link_with_start() -> None:
    addrs = ["Start", "Stop1", "Stop2"]
    order = [0, 1, 2]
    link = build_route_link(
        addrs,
        order,
        TravelMode.DRIVING,
        has_start=True,
        has_end=False,
        route_kind=RouteKind.PATH.value,
        start_resolved="Start",
        end_resolved=None,
    )
    parsed = urlparse(link)
    params = parse_qs(parsed.query)
    assert params["origin"][0] == "Start"
    assert params["destination"][0] == "Stop2"


def test_build_route_link_without_start() -> None:
    addrs = ["A", "B", "C"]
    order = [0, 1, 2]
    link = build_route_link(
        addrs,
        order,
        TravelMode.WALKING,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH.value,
        start_resolved=None,
        end_resolved=None,
    )
    parsed = urlparse(link)
    params = parse_qs(parsed.query)
    assert params["origin"][0] == "A"
    assert params["destination"][0] == "C"


def test_build_route_link_with_fixed_end() -> None:
    addrs = ["A", "B", "End"]
    order = [0, 1, 2]
    link = build_route_link(
        addrs,
        order,
        TravelMode.DRIVING,
        has_start=False,
        has_end=True,
        route_kind=RouteKind.PATH.value,
        start_resolved=None,
        end_resolved="End",
    )
    params = parse_qs(urlparse(link).query)
    assert params["origin"][0] == "A"
    assert params["destination"][0] == "End"


def test_build_route_link_round_trip_origin_equals_destination() -> None:
    addrs = ["Start", "B", "C"]
    order = [0, 1, 2]
    link = build_route_link(
        addrs,
        order,
        TravelMode.DRIVING,
        has_start=True,
        has_end=False,
        route_kind=RouteKind.ROUND_TRIP.value,
        start_resolved="Start",
        end_resolved=None,
    )
    params = parse_qs(urlparse(link).query)
    assert params["origin"][0] == "Start"
    assert params["destination"][0] == "Start"


def test_build_maps_link_rejects_empty_inputs() -> None:
    with pytest.raises(ValidationError):
        build_route_link(
            [],
            [],
            TravelMode.DRIVING,
            has_start=False,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_generate_route_lines_with_start() -> None:
    addrs = ["Start", "Stop1", "Stop2"]
    origs = ["S", "A", "B"]
    order = [0, 1, 2]
    rendered = generate_route_lines(order, addrs, origs, True, False, RouteKind.PATH.value)
    assert "Start" in rendered
    assert "Stop1" in rendered


def test_generate_route_lines_with_fixed_end_includes_end_label() -> None:
    addrs = ["A", "B", "End"]
    origs = ["A", "B", "E"]
    order = [0, 1, 2]
    rendered = generate_route_lines(order, addrs, origs, False, True, RouteKind.PATH.value)
    assert "End:" in rendered
    assert "End" in rendered


def test_generate_route_lines_round_trip_with_start_includes_return() -> None:
    addrs = ["Start", "B", "C"]
    origs = ["S", "B", "C"]
    order = [0, 1, 2]
    rendered = generate_route_lines(order, addrs, origs, True, False, RouteKind.ROUND_TRIP.value)
    assert "Return to start." in rendered


def test_generate_route_lines_round_trip_without_start_includes_return_to_first() -> None:
    addrs = ["A", "B", "C"]
    origs = ["A", "B", "C"]
    order = [0, 1, 2]
    rendered = generate_route_lines(order, addrs, origs, False, False, RouteKind.ROUND_TRIP.value)
    assert "Return to A." in rendered


def test_generate_route_lines_round_trip_rejects_fixed_end() -> None:
    with pytest.raises(ValidationError):
        generate_route_lines(
            [0, 1, 2], ["A", "B", "C"], ["A", "B", "C"], False, True, RouteKind.ROUND_TRIP.value
        )


def test_generate_route_lines_rejects_invalid_fixed_start_order() -> None:
    with pytest.raises(ValidationError):
        generate_route_lines(
            [1, 0, 2],
            ["Start", "B", "C"],
            ["S", "B", "C"],
            True,
            False,
            RouteKind.PATH.value,
        )


def test_generate_route_lines_rejects_invalid_fixed_end_order() -> None:
    with pytest.raises(ValidationError):
        generate_route_lines(
            [0, 2, 1],
            ["A", "B", "End"],
            ["A", "B", "E"],
            False,
            True,
            RouteKind.PATH.value,
        )


def test_generate_route_lines_round_trip_rejects_invalid_fixed_start_order() -> None:
    with pytest.raises(ValidationError):
        generate_route_lines(
            [1, 0, 2],
            ["Start", "B", "C"],
            ["S", "B", "C"],
            True,
            False,
            RouteKind.ROUND_TRIP.value,
        )


def test_generate_route_lines_requires_matching_lengths() -> None:
    with pytest.raises(ValidationError):
        generate_route_lines([0], ["A"], ["A", "B"], False, False, RouteKind.PATH.value)


def test_build_route_link_requires_start() -> None:
    addrs = ["Start", "Stop1", "Stop2"]
    order = [0, 1, 2]
    with pytest.raises(ValidationError):
        build_route_link(
            addrs,
            order,
            TravelMode.DRIVING,
            has_start=True,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_build_route_link_rejects_invalid_order() -> None:
    addrs = ["A", "B"]
    order = [0, 2]
    with pytest.raises(ValidationError):
        build_route_link(
            addrs,
            order,
            TravelMode.DRIVING,
            has_start=False,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_generate_route_lines_invalid_index() -> None:
    with pytest.raises(ValidationError):
        generate_route_lines([2], ["A", "B"], ["A", "B"], False, False, RouteKind.PATH.value)


def test_build_distance_key_validates_inputs() -> None:
    key = build_distance_key("A", "B", "driving", "time")
    assert re.fullmatch(r"distance:v2:[0-9a-f]{64}", key)
    assert "A" not in key
    assert "B" not in key
    assert "driving" not in key


def test_build_distance_key_includes_traffic_variant() -> None:
    key = build_distance_key(
        "A",
        "B",
        "driving",
        "time",
        departure_time="now",
        traffic_model="best_guess",
    )
    without_traffic = build_distance_key("A", "B", "driving", "time")
    assert key != without_traffic


def test_build_distance_key_rejects_non_string_mode_or_metric() -> None:
    with pytest.raises(ValidationError):
        build_distance_key("A", "B", 123, "time")  # type: ignore[arg-type]


def test_build_distance_key_wraps_attribute_errors() -> None:
    class BadStr(str):
        def strip(self, chars: str | None = None) -> BadStr:
            return self

        def lower(self) -> str:  # type: ignore[override]
            raise AttributeError("boom")

    with pytest.raises(ValidationError):
        build_distance_key(BadStr("A"), BadStr("B"), "driving", "time")


def test_build_distance_key_rejects_non_string_inputs() -> None:
    with pytest.raises(ValidationError):
        build_distance_key(1, "B", "driving", "time")


def test_build_maps_link_rejects_missing_order() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A"],
            [],
            TravelMode.DRIVING,
            origin="A",
            destination="A",
            waypoints=[],
        )


def test_build_maps_link_rejects_empty_addresses() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            [],
            [0],
            TravelMode.DRIVING,
            origin="A",
            destination="A",
            waypoints=[],
        )


def test_build_maps_link_rejects_empty_origin_and_destination() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A"],
            [0],
            TravelMode.DRIVING,
            origin="",
            destination="A",
            waypoints=[],
        )
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A"],
            [0],
            TravelMode.DRIVING,
            origin="A",
            destination="",
            waypoints=[],
        )


def test_build_maps_link_rejects_out_of_range_indices() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A", "B"],
            [0, 2],
            TravelMode.DRIVING,
            origin="A",
            destination="B",
            waypoints=[],
        )


def test_build_maps_link_rejects_order_length_mismatch() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A", "B"],
            [0],
            TravelMode.DRIVING,
            origin="A",
            destination="B",
            waypoints=[],
        )


def test_build_maps_link_rejects_non_int_indices() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A", "B"],
            [0, "1"],
            TravelMode.DRIVING,
            origin="A",
            destination="B",
            waypoints=[],
        )


def test_build_route_link_rejects_empty_order() -> None:
    with pytest.raises(ValidationError):
        build_route_link(
            ["A", "B"],
            [],
            TravelMode.DRIVING,
            has_start=False,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_build_route_link_rejects_order_length_mismatch() -> None:
    with pytest.raises(ValidationError):
        build_route_link(
            ["A", "B"],
            [0],
            TravelMode.DRIVING,
            has_start=False,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_build_route_link_round_trip_rejects_fixed_end() -> None:
    addrs = ["A", "B", "C"]
    order = [0, 1, 2]
    with pytest.raises(ValidationError):
        build_route_link(
            addrs,
            order,
            TravelMode.DRIVING,
            has_start=False,
            has_end=True,
            route_kind=RouteKind.ROUND_TRIP.value,
            start_resolved=None,
            end_resolved="C",
        )


def test_build_route_link_requires_fixed_start_order() -> None:
    addrs = ["Start", "B", "C"]
    order = [1, 0, 2]
    with pytest.raises(ValidationError):
        build_route_link(
            addrs,
            order,
            TravelMode.DRIVING,
            has_start=True,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved="Start",
            end_resolved=None,
        )


def test_build_route_link_rejects_non_int_order_indices() -> None:
    with pytest.raises(ValidationError):
        build_route_link(
            ["A", "B"],
            [0, "1"],
            TravelMode.DRIVING,
            has_start=False,
            has_end=False,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_build_route_link_requires_end_resolved_when_fixed_end() -> None:
    with pytest.raises(ValidationError):
        build_route_link(
            ["A", "B", "End"],
            [0, 1, 2],
            TravelMode.DRIVING,
            has_start=False,
            has_end=True,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved=None,
        )


def test_build_route_link_round_trip_requires_fixed_start_order() -> None:
    with pytest.raises(ValidationError):
        build_route_link(
            ["Start", "B", "C"],
            [1, 0, 2],
            TravelMode.DRIVING,
            has_start=True,
            has_end=False,
            route_kind=RouteKind.ROUND_TRIP.value,
            start_resolved="Start",
            end_resolved=None,
        )


def test_build_route_link_with_fixed_start_and_end() -> None:
    addrs = ["Start", "B", "End"]
    order = [0, 1, 2]
    link = build_route_link(
        addrs,
        order,
        TravelMode.DRIVING,
        has_start=True,
        has_end=True,
        route_kind=RouteKind.PATH.value,
        start_resolved="Start",
        end_resolved="End",
    )
    params = parse_qs(urlparse(link).query)
    assert params["origin"][0] == "Start"
    assert params["destination"][0] == "End"


def test_build_route_link_requires_fixed_end_order() -> None:
    addrs = ["A", "B", "End"]
    order = [2, 0, 1]
    with pytest.raises(ValidationError):
        build_route_link(
            addrs,
            order,
            TravelMode.DRIVING,
            has_start=False,
            has_end=True,
            route_kind=RouteKind.PATH.value,
            start_resolved=None,
            end_resolved="End",
        )


def test_build_route_link_round_trip_without_start_sets_destination_origin() -> None:
    addrs = ["A", "B", "C"]
    order = [0, 1, 2]
    link = build_route_link(
        addrs,
        order,
        TravelMode.DRIVING,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.ROUND_TRIP.value,
        start_resolved=None,
        end_resolved=None,
    )
    params = parse_qs(urlparse(link).query)
    assert params["origin"][0] == "A"
    assert params["destination"][0] == "A"


def test_build_maps_link_single_start_address() -> None:
    link = build_maps_link(
        ["Only"],
        [0],
        TravelMode.DRIVING,
        origin="Start",
        destination="Only",
        waypoints=[],
    )
    assert "origin=" in link


def test_build_maps_link_encodes_waypoints_exactly_once() -> None:
    """Waypoint text must survive one standard query-string decode unchanged."""
    link = build_maps_link(
        ["A", "New York, NY", "Montréal, QC", "C"],
        [0, 1, 2, 3],
        TravelMode.DRIVING,
        origin="A",
        destination="C",
        waypoints=["New York, NY", "Montréal, QC"],
    )

    params = parse_qs(urlparse(link).query)
    assert params["waypoints"] == ["New York, NY|Montréal, QC"]
    assert "%25" not in urlparse(link).query


def test_build_maps_link_raises_on_bad_waypoints() -> None:
    with pytest.raises(ValidationError):
        build_maps_link(
            ["A", "B", "C"],
            [0, 1, 2],
            TravelMode.DRIVING,
            origin="A",
            destination="C",
            waypoints=[None],
        )
    with pytest.raises(ValidationError):
        build_distance_key("", "B", "driving", "time")
    with pytest.raises(ValidationError):
        build_distance_key("A", "B", "", "time")
