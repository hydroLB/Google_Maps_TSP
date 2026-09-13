from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from fastest_route.infrastructure.cache.geocode_cache import GeocodeCache, GeocodeDiskCache
from fastest_route.shared.errors import CacheError

if TYPE_CHECKING:
    from pathlib import Path


def test_geocode_cache_normalizes_keys_in_memory() -> None:
    cache = GeocodeCache(memory_max_items=10, disk_path=None, disk_ttl_seconds=60)
    cache.set("  1600  Amphitheatre   Pkwy  ", "1600 Amphitheatre Parkway, Mountain View, CA")
    assert cache.get("1600 amphitheatre pkwy") == "1600 Amphitheatre Parkway, Mountain View, CA"


def test_geocode_cache_disk_persist_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "geocode_cache.json"
    cache = GeocodeCache(memory_max_items=2, disk_path=path, disk_ttl_seconds=60)
    cache.set("A", "Resolved A")
    cache.persist()
    reloaded = GeocodeCache(memory_max_items=2, disk_path=path, disk_ttl_seconds=60)
    assert reloaded.get("a") == "Resolved A"


def test_geocode_disk_cache_secures_existing_plaintext_file(tmp_path: Path) -> None:
    path = tmp_path / "geocode_cache.json"
    path.write_text("{}", encoding="utf-8")
    path.chmod(0o644)

    GeocodeDiskCache(path, ttl_seconds=60)

    assert path.stat().st_mode & 0o777 == 0o600


def test_geocode_cache_disk_ttl_expiry(tmp_path: Path) -> None:
    path = tmp_path / "geocode_cache.json"
    cache = GeocodeCache(memory_max_items=2, disk_path=path, disk_ttl_seconds=1)
    cache.set("A", "Resolved A")
    cache.persist()

    reloaded = GeocodeCache(memory_max_items=1, disk_path=path, disk_ttl_seconds=1)
    disk = reloaded._disk
    assert disk is not None
    disk._data["a"]["timestamp"] = time.time() - 100.0
    assert reloaded.get("A") is None


def test_geocode_cache_populates_memory_from_disk(tmp_path: Path) -> None:
    path = tmp_path / "geocode_cache.json"
    cache = GeocodeCache(memory_max_items=1, disk_path=path, disk_ttl_seconds=60)
    cache.set("A", "Resolved A")
    cache.persist()

    reloaded = GeocodeCache(memory_max_items=1, disk_path=path, disk_ttl_seconds=60)
    assert reloaded.get("A") == "Resolved A"
    assert reloaded._memory.get("a") == "Resolved A"


def test_geocode_cache_rejects_empty_key() -> None:
    cache = GeocodeCache(memory_max_items=2, disk_path=None, disk_ttl_seconds=60)
    with pytest.raises(CacheError):
        cache.get(" ")


def test_geocode_cache_persist_is_noop_without_disk() -> None:
    cache = GeocodeCache(memory_max_items=2, disk_path=None, disk_ttl_seconds=60)
    cache.persist()


def test_geocode_disk_cache_rejects_invalid_ttl(tmp_path: Path) -> None:
    with pytest.raises(CacheError):
        GeocodeDiskCache(tmp_path / "geocode_cache.json", ttl_seconds=0)


def test_geocode_disk_cache_load_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "geocode_cache.json"
    path.write_text("{not-json")
    with pytest.raises(CacheError):
        GeocodeDiskCache(path, ttl_seconds=60)


def test_geocode_disk_cache_load_non_mapping_raises(tmp_path: Path) -> None:
    path = tmp_path / "geocode_cache.json"
    path.write_text("[]")
    with pytest.raises(CacheError):
        GeocodeDiskCache(path, ttl_seconds=60)


def test_geocode_disk_cache_rejects_empty_key(tmp_path: Path) -> None:
    cache = GeocodeDiskCache(tmp_path / "geocode_cache.json", ttl_seconds=60)
    with pytest.raises(CacheError):
        cache.get(" ")


def test_geocode_cache_rejects_invalid_memory_max_items(tmp_path: Path) -> None:
    with pytest.raises(CacheError):
        GeocodeCache(
            memory_max_items=0, disk_path=tmp_path / "geocode_cache.json", disk_ttl_seconds=60
        )
