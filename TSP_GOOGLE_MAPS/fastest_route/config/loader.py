"""Configuration loader and parsing helpers."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from fastest_route.config.loading.accessors import get_mapping
from fastest_route.config.loading.sections import (
    load_cache_config,
    load_environment,
    load_google_maps_config,
    load_http_config,
    load_logging_config,
    load_rate_limit_config,
    load_routing_config,
    load_ui_config,
)
from fastest_route.config.registry import AppConfig
from fastest_route.shared.errors import ConfigError

DEFAULT_CONFIG_NAME = "config.toml"
PACKAGED_CONFIG_NAME = "default.toml"


def _default_config_path() -> Path:
    """Determine the default config path relative to the package."""
    location = "fastest_route.config.loader._default_config_path"
    try:
        loader_path = Path(__file__).resolve()
        source_config = loader_path.parent.parent.parent / DEFAULT_CONFIG_NAME
        if source_config.parent.name == "TSP_GOOGLE_MAPS" and source_config.is_file():
            return source_config
        return loader_path.parent / PACKAGED_CONFIG_NAME
    except OSError as exc:
        raise ConfigError(location, "Failed to resolve default config path.") from exc


def _read_toml(path: Path) -> Mapping[str, object]:
    """Load TOML configuration from disk."""
    location = "fastest_route.config.loader._read_toml"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(location, f"Failed to read config file at {path}.") from exc
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(location, f"Invalid TOML in {path}.") from exc
    if not isinstance(data, Mapping):
        raise ConfigError(location, "Config file did not parse to a mapping.")
    return data


def load_config() -> AppConfig:
    """Load and validate application configuration."""
    location = "fastest_route.config.loader.load_config"
    try:
        config_path = os.environ.get("FASTEST_ROUTE_CONFIG_PATH", "").strip()
        path = Path(config_path) if config_path else _default_config_path()
        data = _read_toml(path)

        app_section = get_mapping(data, "app", location)
        google_section = get_mapping(data, "google_maps", location)
        cache_section = get_mapping(data, "cache", location)
        routing_section = get_mapping(data, "routing", location)
        http_section = get_mapping(data, "http", location)
        rate_section = get_mapping(data, "rate_limit", location)
        logging_section = get_mapping(data, "logging", location)
        ui_section = get_mapping(data, "ui", location)

        environment = load_environment(app_section=app_section, env=os.environ, location=location)
        google_maps = load_google_maps_config(
            google_section=google_section, env=os.environ, location=location
        )
        cache = load_cache_config(cache_section=cache_section, location=location)
        routing = load_routing_config(routing_section=routing_section, location=location)
        http = load_http_config(http_section=http_section, location=location)
        rate_limit = load_rate_limit_config(rate_section=rate_section, location=location)
        logging_cfg = load_logging_config(
            logging_section=logging_section, env=os.environ, location=location
        )
        ui = load_ui_config(ui_section=ui_section, location=location)

        config = AppConfig(
            environment=environment,
            google_maps=google_maps,
            cache=cache,
            routing=routing,
            http=http,
            rate_limit=rate_limit,
            logging=logging_cfg,
            ui=ui,
        )
        config.validate()
        return config
    except ConfigError as exc:
        raise ConfigError(location, f"Config load failed. {exc}") from exc
    except (OSError, TypeError, ValueError) as exc:
        raise ConfigError(location, "Config load failed due to invalid data.") from exc


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Load config once and return a cached instance."""
    location = "fastest_route.config.loader.get_config"
    try:
        return load_config()
    except ConfigError as exc:
        raise ConfigError(location, f"Failed to load config. {exc}") from exc
