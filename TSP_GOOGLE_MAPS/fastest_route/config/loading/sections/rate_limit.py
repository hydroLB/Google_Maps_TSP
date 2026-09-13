"""Rate limit configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_float, get_int
from fastest_route.config.registry import RateLimitConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_rate_limit_config(*, rate_section: Mapping[str, object], location: str) -> RateLimitConfig:
    """Build a RateLimitConfig from the TOML rate_limit section."""
    return RateLimitConfig(
        requests_per_second=get_float(rate_section, "requests_per_second", 5.0, location),
        burst=get_int(rate_section, "burst", 10, location),
        max_wait_seconds=get_float(rate_section, "max_wait_seconds", 10.0, location),
    )
