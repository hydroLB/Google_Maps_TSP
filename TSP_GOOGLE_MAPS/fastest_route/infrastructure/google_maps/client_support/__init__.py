"""Focused request, traffic, and matrix mixins for ``GoogleMapsClient``."""

from fastest_route.infrastructure.google_maps.client_support.matrix import (
    GoogleMapsClientMatrixMixin,
)
from fastest_route.infrastructure.google_maps.client_support.requests import (
    GoogleMapsClientRequestMixin,
)
from fastest_route.infrastructure.google_maps.client_support.traffic import (
    GoogleMapsClientTrafficMixin,
)

__all__ = [
    "GoogleMapsClientMatrixMixin",
    "GoogleMapsClientRequestMixin",
    "GoogleMapsClientTrafficMixin",
]
