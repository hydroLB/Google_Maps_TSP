"""HTTP configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_float, get_int, get_sequence_int
from fastest_route.config.registry import HttpConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_http_config(*, http_section: Mapping[str, object], location: str) -> HttpConfig:
    """Build an HttpConfig from the TOML http section."""
    return HttpConfig(
        timeout_seconds=get_float(http_section, "timeout_seconds", 10.0, location),
        retry_max_attempts=get_int(http_section, "retry_max_attempts", 3, location),
        retry_base_delay_seconds=get_float(http_section, "retry_base_delay_seconds", 0.4, location),
        retry_max_delay_seconds=get_float(http_section, "retry_max_delay_seconds", 6.0, location),
        retry_jitter_ratio=get_float(http_section, "retry_jitter_ratio", 0.2, location),
        retry_statuses=get_sequence_int(
            http_section, "retry_statuses", (429, 500, 502, 503, 504), location
        ),
    )
