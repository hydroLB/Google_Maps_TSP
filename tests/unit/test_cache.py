from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from fastest_route.infrastructure.cache import persistence as persistence_module
from fastest_route.infrastructure.cache.distance_cache import DistanceCache
from fastest_route.infrastructure.cache.keys import build_distance_key
from fastest_route.infrastructure.cache.lru_cache import LruCache
from fastest_route.infrastructure.cache.store import CacheStore
from fastest_route.shared.errors import CacheError


def test_lru_cache_eviction() -> None:
    cache = LruCache[str, int](max_items=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert list(cache.keys()) == ["b", "c"]
    assert list(cache.items()) == [("b", 2), ("c", 3)]
    cache.clear()
    assert list(cache.keys()) == []


def test_lru_cache_invalid_size() -> None:
    with pytest.raises(CacheError):
        LruCache[str, int](max_items=0)


def test_lru_cache_lock_errors() -> None:
    cache = LruCache[str, int](max_items=1)

    class BadLock:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    cache._lock = BadLock()
    with pytest.raises(CacheError):
        cache.get("a")
    with pytest.raises(CacheError):
        cache.set("a", 1)
    with pytest.raises(CacheError):
        cache.keys()
    with pytest.raises(CacheError):
        list(cache.items())
    with pytest.raises(CacheError):
        cache.clear()


def test_distance_cache_persist_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    cache = DistanceCache(path, ttl_seconds=10)
    key = build_distance_key("A", "B", "driving", "time")
    cache.set(key, 5.0)
    cache.persist()
    reloaded = DistanceCache(path, ttl_seconds=10)
    assert reloaded.get(key) == 5.0
    assert path.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".cache.json.*.tmp"))


def test_distance_cache_atomic_write_cleans_up_after_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed atomic replace must not leave sensitive temporary cache files behind."""

    path = tmp_path / "cache.json"
    cache = DistanceCache(path, ttl_seconds=10)
    cache.set("key", 5.0)
    monkeypatch.setattr(
        persistence_module.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(CacheError, match="persist"):
        cache.persist()
    assert not path.exists()
    assert not list(tmp_path.glob(".cache.json.*.tmp"))


def test_distance_cache_invalid_ttl() -> None:
    with pytest.raises(CacheError):
        DistanceCache(Path("cache.json"), ttl_seconds=0)


def test_distance_cache_ttl_expiry(tmp_path: Path) -> None:
    cache = DistanceCache(tmp_path / "cache.json", ttl_seconds=1)
    cache.set("key", 5.0)
    cache._data["key"]["timestamp"] = time.time() - 100.0
    assert cache.get("key") is None


def test_distance_cache_load_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text("{invalid")
    with pytest.raises(CacheError):
        DistanceCache(path, ttl_seconds=10)


def test_distance_cache_load_requires_mapping(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text("[1, 2]")
    with pytest.raises(CacheError):
        DistanceCache(path, ttl_seconds=10)


def test_distance_cache_load_skips_invalid_entries(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    good_key = build_distance_key("A", "B", "driving", "time")
    payload = {"bad": 5, good_key: {"value": 2, "timestamp": time.time()}}
    path.write_text(json.dumps(payload))
    cache = DistanceCache(path, ttl_seconds=10)
    assert cache.get(good_key) == 2.0


def test_distance_cache_migrates_plaintext_legacy_keys_and_permissions(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text(
        json.dumps(
            {
                "driving|time|1600 amphitheatre parkway|1 market street": {
                    "value": 2,
                    "timestamp": time.time(),
                }
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o644)

    cache = DistanceCache(path, ttl_seconds=10)

    assert cache._data == {}
    assert json.loads(path.read_text(encoding="utf-8")) == {}
    assert path.stat().st_mode & 0o777 == 0o600


def test_distance_cache_prune_error_raises(tmp_path: Path) -> None:
    cache = DistanceCache(tmp_path / "cache.json", ttl_seconds=10)

    class BadData:
        def items(self):
            raise RuntimeError("boom")

    cache._data = BadData()
    with pytest.raises(CacheError):
        cache._prune()


def test_distance_cache_lock_errors(tmp_path: Path) -> None:
    cache = DistanceCache(tmp_path / "cache.json", ttl_seconds=10)

    class BadLock:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    cache._lock = BadLock()
    with pytest.raises(CacheError):
        cache.get("key")
    with pytest.raises(CacheError):
        cache.set("key", 1.0)
    with pytest.raises(CacheError):
        cache.persist()


def test_cache_store_routes() -> None:
    store = CacheStore(route_cache_size=10)
    store.cache_route(
        ["A", "B"], "driving", "time", False, False, "path", "none", [0, 1], 5.0, [5.0]
    )
    cached = store.get_cached_route(["A", "B"], "driving", "time", False, False, "path", "none")
    assert cached == ([0, 1], 5.0, [5.0])


def test_cache_store_copies_mutable_route_values_on_write() -> None:
    """Mutating route inputs after caching must not change the stored value."""
    store = CacheStore(route_cache_size=10)
    order = [0, 1]
    legs = [5.0]

    store.cache_route(["A", "B"], "driving", "time", False, False, "path", "none", order, 5.0, legs)
    order.reverse()
    legs[0] = 99.0

    assert store.get_cached_route(["A", "B"], "driving", "time", False, False, "path", "none") == (
        [0, 1],
        5.0,
        [5.0],
    )


def test_cache_store_copies_mutable_route_values_on_read() -> None:
    """Mutating a cache hit must not change values returned by later reads."""
    store = CacheStore(route_cache_size=10)
    store.cache_route(
        ["A", "B"], "driving", "time", False, False, "path", "none", [0, 1], 5.0, [5.0]
    )

    cached = store.get_cached_route(["A", "B"], "driving", "time", False, False, "path", "none")
    assert cached is not None
    cached[0].reverse()
    cached[2][0] = 99.0

    assert store.get_cached_route(["A", "B"], "driving", "time", False, False, "path", "none") == (
        [0, 1],
        5.0,
        [5.0],
    )


def test_cache_store_invalid_sizes_raise() -> None:
    with pytest.raises(CacheError):
        CacheStore(route_cache_size=0)


def test_cache_store_rejects_empty_addresses() -> None:
    store = CacheStore(route_cache_size=10)
    with pytest.raises(CacheError):
        store.cache_route([], "driving", "time", False, False, "path", "none", [0], 1.0, [1.0])
    with pytest.raises(CacheError):
        store.get_cached_route([], "driving", "time", False, False, "path", "none")


def test_cache_store_rejects_empty_legs() -> None:
    store = CacheStore(route_cache_size=10)
    with pytest.raises(CacheError):
        store.cache_route(
            ["A", "B"], "driving", "time", False, False, "path", "none", [0, 1], 5.0, []
        )


def test_cache_store_rejects_empty_traffic_key() -> None:
    store = CacheStore(route_cache_size=10)
    with pytest.raises(CacheError):
        store.cache_route(
            ["A", "B"], "driving", "time", False, False, "path", " ", [0, 1], 5.0, [5.0]
        )
    with pytest.raises(CacheError):
        store.get_cached_route(["A", "B"], "driving", "time", False, False, "path", " ")
