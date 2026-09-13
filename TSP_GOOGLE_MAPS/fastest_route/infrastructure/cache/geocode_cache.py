"""In-memory and optional disk-backed cache for geocoding results with TTL."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING

from fastest_route.infrastructure.cache.lru_cache import LruCache
from fastest_route.infrastructure.cache.persistence import write_json_atomically
from fastest_route.shared.errors import CacheError

if TYPE_CHECKING:
    from pathlib import Path


class GeocodeDiskCache:
    """Persist geocode results to disk with TTL."""

    def __init__(self, path: Path, ttl_seconds: int) -> None:
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeDiskCache.__init__"
        if ttl_seconds <= 0:
            raise CacheError(location, "ttl_seconds must be positive.")
        self._path = path.expanduser()
        self._ttl_seconds = int(ttl_seconds)
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, object]] = {}
        self._load()

    def _load(self) -> None:
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeDiskCache._load"
        if not self._path.exists():
            return
        try:
            os.chmod(self._path, 0o600)
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CacheError(location, "Failed to load cache file.") from exc
        if not isinstance(payload, Mapping):
            raise CacheError(location, "Cache file did not contain a mapping.")
        for key, entry in payload.items():
            if not isinstance(key, str) or not isinstance(entry, Mapping):
                continue
            value = entry.get("value")
            timestamp = entry.get("timestamp")
            if isinstance(value, str) and isinstance(timestamp, int | float):
                self._data[key] = {"value": value, "timestamp": float(timestamp)}

    def _prune(self) -> None:
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeDiskCache._prune"
        try:
            now = time.time()
            expired: list[str] = []
            for key, entry in self._data.items():
                ts = entry.get("timestamp", 0.0)
                if isinstance(ts, int | float) and now - float(ts) > self._ttl_seconds:
                    expired.append(key)
            for key in expired:
                self._data.pop(key, None)
        except RuntimeError as exc:
            raise CacheError(location, "Failed to prune cache entries.") from exc

    def get(self, key: str) -> str | None:
        """Retrieve a cached value if it is fresh."""
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeDiskCache.get"
        if not isinstance(key, str) or not key.strip():
            raise CacheError(location, "key must be a non empty string.")
        try:
            with self._lock:
                self._prune()
                entry = self._data.get(key)
                if entry is None:
                    return None
                value = entry.get("value")
                return value if isinstance(value, str) else None
        except RuntimeError as exc:
            raise CacheError(location, "Failed to read cache entry.") from exc

    def set(self, key: str, value: str) -> None:
        """Store a cached formatted address with the current timestamp."""
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeDiskCache.set"
        if not isinstance(key, str) or not key.strip():
            raise CacheError(location, "key must be a non empty string.")
        if not isinstance(value, str) or not value.strip():
            raise CacheError(location, "value must be a non empty string.")
        try:
            with self._lock:
                self._data[key] = {"value": value, "timestamp": float(time.time())}
        except RuntimeError as exc:
            raise CacheError(location, "Failed to write cache entry.") from exc

    def persist(self) -> None:
        """Persist cached entries to disk."""
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeDiskCache.persist"
        try:
            with self._lock:
                self._prune()
                write_json_atomically(self._path, self._data)
        except (OSError, RuntimeError) as exc:
            raise CacheError(location, "Failed to persist cache to disk.") from exc


class GeocodeCache:
    """Combined in-memory LRU cache with optional disk persistence for geocoding results."""

    def __init__(
        self,
        *,
        memory_max_items: int,
        disk_path: Path | None,
        disk_ttl_seconds: int,
    ) -> None:
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeCache.__init__"
        if not isinstance(memory_max_items, int) or memory_max_items <= 0:
            raise CacheError(location, "memory_max_items must be a positive integer.")
        if disk_path is not None and not str(disk_path).strip():
            raise CacheError(location, "disk_path must be a non empty path when provided.")
        self._memory = LruCache[str, str](max_items=memory_max_items)
        self._disk: GeocodeDiskCache | None = (
            GeocodeDiskCache(disk_path, ttl_seconds=disk_ttl_seconds)
            if disk_path is not None
            else None
        )

    def get(self, key: str) -> str | None:
        """Retrieve a cached formatted address."""
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeCache.get"
        if not isinstance(key, str) or not key.strip():
            raise CacheError(location, "key must be a non empty string.")
        normalized = " ".join(key.strip().lower().split())
        value = self._memory.get(normalized)
        if value is not None:
            return value
        if self._disk is None:
            return None
        disk_value = self._disk.get(normalized)
        if disk_value is not None:
            self._memory.set(normalized, disk_value)
        return disk_value

    def set(self, key: str, value: str) -> None:
        """Store a formatted address in cache."""
        location = "fastest_route.infrastructure.cache.geocode_cache.GeocodeCache.set"
        if not isinstance(key, str) or not key.strip():
            raise CacheError(location, "key must be a non empty string.")
        if not isinstance(value, str) or not value.strip():
            raise CacheError(location, "value must be a non empty string.")
        normalized = " ".join(key.strip().lower().split())
        formatted = value.strip()
        self._memory.set(normalized, formatted)
        if self._disk is not None:
            self._disk.set(normalized, formatted)

    def persist(self) -> None:
        """Persist disk cache entries when disk caching is enabled."""
        if self._disk is None:
            return
        self._disk.persist()
