"""Application-level configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_str

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_environment(
    *, app_section: Mapping[str, object], env: Mapping[str, str], location: str
) -> str:
    """Determine the application environment with environment-variable precedence."""
    env_value = env.get("FASTEST_ROUTE_ENV", "").strip()
    if env_value:
        return env_value
    return get_str(app_section, "environment", "dev", location).strip()
