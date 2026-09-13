from __future__ import annotations

import pytest

from fastest_route.infrastructure.google_maps.parsing import (
    parse_distance_matrix_value,
    parse_distance_matrix_values,
)
from fastest_route.shared.errors import ExternalServiceError
from fastest_route.shared.types import OptimizeFor


def test_parse_distance_matrix_value_uses_duration_in_traffic_when_enabled() -> None:
    payload: dict[str, object] = {
        "status": "OK",
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration": {"value": 600},
                        "duration_in_traffic": {"value": 900},
                        "distance": {"value": 1000},
                    }
                ]
            }
        ],
    }
    minutes = parse_distance_matrix_value(
        payload,
        metric=OptimizeFor.TIME,
        use_duration_in_traffic=True,
        location="test",
    )
    assert minutes == 15.0


def test_parse_distance_matrix_value_traffic_missing_raises() -> None:
    payload: dict[str, object] = {
        "status": "OK",
        "rows": [
            {"elements": [{"status": "OK", "duration": {"value": 600}, "distance": {"value": 1}}]}
        ],
    }
    with pytest.raises(ExternalServiceError):
        parse_distance_matrix_value(
            payload,
            metric=OptimizeFor.TIME,
            use_duration_in_traffic=True,
            location="test",
        )


def test_parse_distance_matrix_values_rejects_partial_response() -> None:
    """A provider response with the wrong shape must never become a partial route."""

    payload: dict[str, object] = {
        "status": "OK",
        "rows": [{"elements": [{"status": "OK", "duration": {"value": 0}}]}],
    }
    with pytest.raises(ExternalServiceError, match="row count"):
        parse_distance_matrix_values(
            payload,
            metric=OptimizeFor.TIME,
            expected_size=2,
            location="test",
        )


@pytest.mark.parametrize(
    ("diagonal_element", "message"),
    [
        ("invalid", r"element \(0, 0\) was invalid"),
        ({"status": "NOT_FOUND", "duration": {"value": 0}}, "element status NOT_FOUND"),
        ({"status": "OK"}, "Duration payload missing"),
        ({"status": "OK", "duration": {"value": "zero"}}, "Duration value missing"),
    ],
)
def test_parse_distance_matrix_values_validates_diagonal_element(
    diagonal_element: object,
    message: str,
) -> None:
    """Diagonal elements must satisfy the same provider contract as directed legs."""

    payload: dict[str, object] = {
        "status": "OK",
        "rows": [{"elements": [diagonal_element]}],
    }

    with pytest.raises(ExternalServiceError, match=message):
        parse_distance_matrix_values(
            payload,
            metric=OptimizeFor.TIME,
            expected_size=1,
            location="test",
        )


def test_parse_distance_matrix_values_normalizes_valid_diagonal_to_zero() -> None:
    """A valid provider self-cost is normalized instead of exposed to the solver."""

    payload: dict[str, object] = {
        "status": "OK",
        "rows": [{"elements": [{"status": "OK", "duration": {"value": 30}}]}],
    }

    assert parse_distance_matrix_values(
        payload,
        metric=OptimizeFor.TIME,
        expected_size=1,
        location="test",
    ) == [[0.0]]
