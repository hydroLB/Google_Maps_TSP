"""Cache configuration section builder."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastest_route.config.loading.accessors import get_int, get_str
from fastest_route.config.registry import CacheConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def load_cache_config(*, cache_section: Mapping[str, object], location: str) -> CacheConfig:
    """Build a CacheConfig from the TOML cache section."""
    cache_path_raw = get_str(
        cache_section,
        "disk_path",
        str(Path.home() / ".cache" / "fastest_route" / "distance_cache.json"),
        location,
    )
    geocode_disk_path_raw = get_str(cache_section, "geocode_disk_path", "", location).strip()
    geocode_disk_path = Path(geocode_disk_path_raw).expanduser() if geocode_disk_path_raw else None
    return CacheConfig(
        disk_path=Path(cache_path_raw).expanduser(),
        geocode_disk_path=geocode_disk_path,
        route_cache_size=get_int(cache_section, "route_cache_size", 200, location),
        disk_cache_ttl_seconds=get_int(cache_section, "disk_cache_ttl_seconds", 86400, location),
        geocode_cache_size=get_int(cache_section, "geocode_cache_size", 500, location),
        geocode_disk_cache_ttl_seconds=get_int(
            cache_section, "geocode_disk_cache_ttl_seconds", 86400, location
        ),
    )
