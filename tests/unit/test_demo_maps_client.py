"""Tests for the deterministic, network-free maps demo client."""

from __future__ import annotations

import pytest

from fastest_route.infrastructure.demo.maps_client import DEMO_LANDMARKS, DemoMapsClient
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import CancellationError, ValidationError
from fastest_route.shared.types import OptimizeFor, TravelMode


def test_demo_client_geocodes_and_suggests_only_disclosed_fixtures() -> None:
    client = DemoMapsClient()

    assert client.has_api_key()
    assert client.geocode("Grand Central") == DEMO_LANDMARKS[0].name
    assert client.autocomplete("museum") == [DEMO_LANDMARKS[5].name]
    assert set(client.autocomplete("new york")) <= {landmark.name for landmark in DEMO_LANDMARKS}


def test_demo_client_rejects_unknown_addresses_clearly() -> None:
    client = DemoMapsClient()

    with pytest.raises(ValidationError, match="not available offline"):
        client.geocode("Times Square")
    with pytest.raises(ValidationError, match="not in the offline demo fixture"):
        client.build_matrix(
            [DEMO_LANDMARKS[0].name, "Times Square"],
            TravelMode.WALKING,
            OptimizeFor.DISTANCE,
            cancellation_token=CancellationToken(),
            max_seconds=1.0,
        )


@pytest.mark.parametrize("metric", [OptimizeFor.DISTANCE, OptimizeFor.TIME])
def test_demo_matrix_is_square_deterministic_and_nonnegative(metric: OptimizeFor) -> None:
    client = DemoMapsClient()
    addresses = [landmark.name for landmark in DEMO_LANDMARKS[:5]]
    token = CancellationToken()

    first = client.build_matrix(
        addresses,
        TravelMode.DRIVING,
        metric,
        cancellation_token=token,
        max_seconds=1.0,
    )
    second = client.build_matrix(
        addresses,
        TravelMode.DRIVING,
        metric,
        cancellation_token=token,
        max_seconds=1.0,
    )

    assert first == second
    assert len(first) == len(addresses)
    assert all(len(row) == len(addresses) for row in first)
    assert all(value >= 0.0 for row in first for value in row)
    assert all(first[index][index] == 0.0 for index in range(len(first)))


def test_demo_matrix_respects_cancellation() -> None:
    token = CancellationToken()
    token.cancel()

    with pytest.raises(CancellationError, match="Operation cancelled by caller"):
        DemoMapsClient().build_matrix(
            [landmark.name for landmark in DEMO_LANDMARKS[:3]],
            TravelMode.BICYCLING,
            OptimizeFor.TIME,
            cancellation_token=token,
            max_seconds=1.0,
        )


def test_demo_route_cache_key_is_stable() -> None:
    client = DemoMapsClient()

    assert client.get_route_cache_key(
        mode=TravelMode.TRANSIT, metric=OptimizeFor.TIME
    ) == client.get_route_cache_key(mode=TravelMode.TRANSIT, metric=OptimizeFor.TIME)
