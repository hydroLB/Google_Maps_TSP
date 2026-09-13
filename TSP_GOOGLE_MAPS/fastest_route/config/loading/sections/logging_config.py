"""Logging configuration section builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_str
from fastest_route.config.registry import LoggingConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_logging_config(
    *, logging_section: Mapping[str, object], env: Mapping[str, str], location: str
) -> LoggingConfig:
    """Build a LoggingConfig with environment-variable precedence."""
    level_override = env.get("FASTEST_ROUTE_LOG_LEVEL", "").strip()
    level = (
        level_override if level_override else get_str(logging_section, "level", "INFO", location)
    )
    return LoggingConfig(level=level)
