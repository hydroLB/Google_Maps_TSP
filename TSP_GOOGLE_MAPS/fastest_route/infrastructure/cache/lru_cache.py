"""Thread safe in memory LRU cache implementation."""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import TYPE_CHECKING, Generic, TypeVar

from fastest_route.shared.errors import CacheError

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


class LruCache(Generic[KeyT, ValueT]):
    """Provide a thread safe least recently used cache."""

    def __init__(self, max_items: int) -> None:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.__init__"
        try:
            if max_items <= 0:
                raise CacheError(location, "max_items must be positive.")
            self._max_items = max_items
            self._data: OrderedDict[KeyT, ValueT] = OrderedDict()
            self._lock = threading.Lock()
        except CacheError:
            raise
        except RuntimeError as exc:
            raise CacheError(location, "Failed to initialize LRU cache.") from exc

    def get(self, key: KeyT) -> ValueT | None:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.get"
        try:
            with self._lock:
                if key not in self._data:
                    return None
                value = self._data.pop(key)
                self._data[key] = value
                return value
        except RuntimeError as exc:
            raise CacheError(location, "Failed to read from cache.") from exc

    def set(self, key: KeyT, value: ValueT) -> None:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.set"
        try:
            with self._lock:
                if key in self._data:
                    self._data.pop(key)
                self._data[key] = value
                while len(self._data) > self._max_items:
                    self._data.popitem(last=False)
        except RuntimeError as exc:
            raise CacheError(location, "Failed to write to cache.") from exc

    def keys(self) -> Iterable[KeyT]:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.keys"
        try:
            with self._lock:
                return list(self._data.keys())
        except RuntimeError as exc:
            raise CacheError(location, "Failed to read cache keys.") from exc

    def __iter__(self) -> Iterator[KeyT]:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.__iter__"
        try:
            return iter(self.keys())
        except CacheError as exc:
            raise CacheError(location, str(exc)) from exc

    def items(self) -> Iterator[tuple[KeyT, ValueT]]:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.items"
        try:
            with self._lock:
                return iter(list(self._data.items()))
        except RuntimeError as exc:
            raise CacheError(location, "Failed to read cache items.") from exc

    def clear(self) -> None:
        location = "fastest_route.infrastructure.cache.lru_cache.LruCache.clear"
        try:
            with self._lock:
                self._data.clear()
        except RuntimeError as exc:
            raise CacheError(location, "Failed to clear cache.") from exc
