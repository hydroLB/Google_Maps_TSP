"""Disk backed cache for distance matrix values with TTL."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING

from fastest_route.infrastructure.cache.keys import DISTANCE_CACHE_KEY_PREFIX
from fastest_route.infrastructure.cache.persistence import write_json_atomically
from fastest_route.shared.errors import CacheError

if TYPE_CHECKING:
    from pathlib import Path


class DistanceCache:
    """Persist distance or time values to disk with TTL."""

    def __init__(self, path: Path, ttl_seconds: int) -> None:
        location = "fastest_route.infrastructure.cache.distance_cache.DistanceCache.__init__"
        if ttl_seconds <= 0:
            raise CacheError(location, "ttl_seconds must be positive.")
        self._path = path.expanduser()
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, float]] = {}
        self._load()

    def _load(self) -> None:
        location = "fastest_route.infrastructure.cache.distance_cache.DistanceCache._load"
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CacheError(location, "Failed to load cache file.") from exc
        if not isinstance(payload, Mapping):
            raise CacheError(location, "Cache file did not contain a mapping.")
        discarded_legacy_entries = False
        for key, entry in payload.items():
            if not isinstance(key, str) or not isinstance(entry, Mapping):
                continue
            if not key.startswith(DISTANCE_CACHE_KEY_PREFIX):
                discarded_legacy_entries = True
                continue
            value = entry.get("value")
            timestamp = entry.get("timestamp")
            if isinstance(value, int | float) and isinstance(timestamp, int | float):
                self._data[key] = {"value": float(value), "timestamp": float(timestamp)}
        try:
            if discarded_legacy_entries:
                write_json_atomically(self._path, self._data)
            else:
                os.chmod(self._path, 0o600)
        except OSError as exc:
            raise CacheError(location, "Failed to secure cache file.") from exc

    def _prune(self) -> None:
        location = "fastest_route.infrastructure.cache.distance_cache.DistanceCache._prune"
        try:
            now = time.time()
            expired = [
                key
                for key, entry in self._data.items()
                if now - entry.get("timestamp", 0.0) > self._ttl_seconds
            ]
            for key in expired:
                self._data.pop(key, None)
        except RuntimeError as exc:
            raise CacheError(location, "Failed to prune cache entries.") from exc

    def get(self, key: str) -> float | None:
        """Retrieve a cached value if it is fresh."""
        location = "fastest_route.infrastructure.cache.distance_cache.DistanceCache.get"
        try:
            with self._lock:
                self._prune()
                entry = self._data.get(key)
                if entry is None:
                    return None
                return entry.get("value")
        except RuntimeError as exc:
            raise CacheError(location, "Failed to read cache entry.") from exc

    def set(self, key: str, value: float) -> None:
        """Store a cache value with the current timestamp."""
        location = "fastest_route.infrastructure.cache.distance_cache.DistanceCache.set"
        try:
            with self._lock:
                self._data[key] = {"value": float(value), "timestamp": float(time.time())}
        except RuntimeError as exc:
            raise CacheError(location, "Failed to write cache entry.") from exc

    def persist(self) -> None:
        """Persist in memory cache data to disk."""
        location = "fastest_route.infrastructure.cache.distance_cache.DistanceCache.persist"
        try:
            with self._lock:
                self._prune()
                write_json_atomically(self._path, self._data)
        except (OSError, RuntimeError) as exc:
            raise CacheError(location, "Failed to persist cache to disk.") from exc
