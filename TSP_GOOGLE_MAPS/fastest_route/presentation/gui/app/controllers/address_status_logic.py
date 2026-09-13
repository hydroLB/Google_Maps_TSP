"""Address status computation helpers for the GUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.shared.errors import ExternalServiceError, ValidationError
from fastest_route.shared.utils.address_utils import normalize_address_input

if TYPE_CHECKING:
    from fastest_route.infrastructure.google_maps.client import GoogleMapsClient


def compute_address_status(*, maps_client: GoogleMapsClient, address_raw: object) -> str:
    """Compute the short status code for an address input."""
    if not isinstance(address_raw, str):
        return "ERR"
    address = address_raw.strip()
    if not address:
        return ""

    if not maps_client.has_api_key():
        return "KEY"

    try:
        maps_client.geocode(normalize_address_input(address), select_callback=None)
        return "OK"
    except ExternalServiceError:
        return "SERVICE"
    except ValidationError:
        return "ERR"
