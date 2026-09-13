"""Typed accessors for TOML mappings used by the config loader."""

from __future__ import annotations

from collections.abc import Mapping

from fastest_route.shared.errors import ConfigError


def get_mapping(data: object, key: str, location: str) -> Mapping[str, object]:
    """Extract a nested mapping section from parsed config data."""
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config data must be a mapping.")
    if key not in data:
        return {}
    section = data[key]
    if not isinstance(section, Mapping):
        raise ConfigError(location, f"Config section '{key}' must be a table.")
    return section


def get_str(data: object, key: str, default: str, location: str) -> str:
    """Extract a string value from a mapping with a default fallback."""
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config section must be a mapping.")
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(location, f"Config value '{key}' must be a string.")
    return value


def get_int(data: object, key: str, default: int, location: str) -> int:
    """Extract an integer value from a mapping with a default fallback."""
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config section must be a mapping.")
    value = data.get(key, default)
    if not isinstance(value, int):
        raise ConfigError(location, f"Config value '{key}' must be an integer.")
    return value


def get_float(data: object, key: str, default: float, location: str) -> float:
    """Extract a float value from a mapping, accepting ints as floats."""
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config section must be a mapping.")
    value = data.get(key, default)
    if isinstance(value, int):
        return float(value)
    if not isinstance(value, float):
        raise ConfigError(location, f"Config value '{key}' must be a float.")
    return value


def get_bool(data: object, key: str, default: bool, location: str) -> bool:
    """Extract a boolean value from a mapping with a default fallback."""
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config section must be a mapping.")
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(location, f"Config value '{key}' must be a boolean.")
    return value


def get_sequence_int(data: object, key: str, default: tuple[int, ...], location: str) -> list[int]:
    """Extract a list of integers from a mapping with a default fallback."""
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config section must be a mapping.")
    value = data.get(key, list(default))
    if not isinstance(value, list):
        raise ConfigError(location, f"Config value '{key}' must be a list of ints.")
    for item in value:
        if not isinstance(item, int):
            raise ConfigError(location, f"Config value '{key}' must contain ints only.")
    return value
