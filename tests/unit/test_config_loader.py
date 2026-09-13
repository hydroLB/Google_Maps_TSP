from __future__ import annotations

from pathlib import Path

import pytest

from fastest_route.config import loader as loader_module
from fastest_route.config.loader import load_config
from fastest_route.config.loading.accessors import (
    get_float,
    get_int,
    get_mapping,
    get_sequence_int,
    get_str,
)
from fastest_route.config.loading.parsers import parse_optimize_for, parse_travel_mode
from fastest_route.shared.errors import ConfigError


def _write_config(path: Path) -> None:
    content = """
[app]
environment = "test"

[google_maps]
api_key = ""
distance_matrix_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
places_autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"

[cache]
disk_path = "./cache.json"
route_cache_size = 10
disk_cache_ttl_seconds = 60

[routing]
max_exact = 5
two_opt_max_passes = 3
nearest_neighbor_start_index = 0
default_mode = "driving"
default_optimize_for = "time"
max_compute_seconds = 5.0

[http]
timeout_seconds = 1.0
retry_max_attempts = 2
retry_base_delay_seconds = 0.01
retry_max_delay_seconds = 0.05
retry_jitter_ratio = 0.0
retry_statuses = [429, 500]

[rate_limit]
requests_per_second = 100.0
burst = 10
max_wait_seconds = 1.0

[logging]
level = "INFO"

[ui]
min_stops = 3
max_stops = 7
autocomplete_min_chars = 3
autocomplete_delay_ms = 50
status_delay_ms = 50
"""
    path.write_text(content.strip())


def test_load_config_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "env-key")
    config = load_config()
    assert config.google_maps.api_key == "env-key"
    assert config.cache.route_cache_size == 10


def test_load_config_invalid_value_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    content = config_path.read_text().replace("max_exact = 5", "max_exact = 0")
    config_path.write_text(content)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    with pytest.raises(ConfigError):
        load_config()


def test_default_config_path_points_to_repo() -> None:
    path = loader_module._default_config_path()
    assert path.name == "config.toml"


def test_installed_default_ignores_unrelated_site_packages_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site_packages = tmp_path / "site-packages"
    package_config = site_packages / "fastest_route" / "config"
    package_config.mkdir(parents=True)
    loader_path = package_config / "loader.py"
    loader_path.write_text("", encoding="utf-8")
    packaged_default = package_config / "default.toml"
    packaged_default.write_text("[app]\nenvironment='dev'\n", encoding="utf-8")
    (site_packages / "config.toml").write_text("[app]\nenvironment='unrelated'\n", encoding="utf-8")
    monkeypatch.setattr(loader_module, "__file__", str(loader_path))

    assert loader_module._default_config_path() == packaged_default


def test_default_config_path_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_oserror(self: Path) -> Path:
        raise OSError("boom")

    monkeypatch.setattr(Path, "resolve", raise_oserror)
    with pytest.raises(ConfigError):
        loader_module._default_config_path()


def test_read_toml_invalid_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("not = [")
    with pytest.raises(ConfigError):
        loader_module._read_toml(config_path)


def test_read_toml_read_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"

    def raise_oserror(self: Path) -> bytes:
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_bytes", raise_oserror)
    with pytest.raises(ConfigError):
        loader_module._read_toml(config_path)


def test_read_toml_requires_mapping(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("value = 1")
    monkeypatch.setattr(loader_module.tomllib, "loads", lambda *_args, **_kwargs: ["bad"])
    with pytest.raises(ConfigError):
        loader_module._read_toml(config_path)


def test_get_str_invalid_type_raises() -> None:
    with pytest.raises(ConfigError):
        get_str({"value": 1}, "value", "x", "test")


def test_get_int_invalid_type_raises() -> None:
    with pytest.raises(ConfigError):
        get_int({"value": "1"}, "value", 1, "test")


def test_get_float_invalid_type_raises() -> None:
    with pytest.raises(ConfigError):
        get_float({"value": "1.0"}, "value", 1.0, "test")


def test_get_sequence_int_invalid_type_raises() -> None:
    with pytest.raises(ConfigError):
        get_sequence_int({"value": [1, "2"]}, "value", (1,), "test")


def test_parse_travel_mode_invalid_raises() -> None:
    with pytest.raises(ConfigError):
        parse_travel_mode("fly", "test")


def test_parse_optimize_for_invalid_raises() -> None:
    with pytest.raises(ConfigError):
        parse_optimize_for("speed", "test")


def test_get_mapping_returns_empty_when_missing() -> None:
    result = get_mapping({}, "missing", "test")
    assert result == {}


def test_get_mapping_invalid_type_raises() -> None:
    with pytest.raises(ConfigError):
        get_mapping({"section": "bad"}, "section", "test")


def test_get_float_accepts_int() -> None:
    value = get_float({"value": 1}, "value", 1.0, "test")
    assert value == 1.0


def test_get_sequence_int_non_list_raises() -> None:
    with pytest.raises(ConfigError):
        get_sequence_int({"value": "bad"}, "value", (1,), "test")


def test_get_mapping_non_mapping_data_raises() -> None:
    with pytest.raises(ConfigError):
        get_mapping(None, "section", "test")


def test_get_str_non_mapping_data_raises() -> None:
    with pytest.raises(ConfigError):
        get_str(123, "value", "x", "test")


def test_get_int_non_mapping_data_raises() -> None:
    with pytest.raises(ConfigError):
        get_int(123, "value", 1, "test")


def test_get_float_non_mapping_data_raises() -> None:
    with pytest.raises(ConfigError):
        get_float(123, "value", 1.0, "test")


def test_get_sequence_int_non_mapping_data_raises() -> None:
    with pytest.raises(ConfigError):
        get_sequence_int(123, "value", (1,), "test")


def test_parse_travel_mode_non_string_raises() -> None:
    with pytest.raises(ConfigError):
        parse_travel_mode(123, "test")


def test_parse_optimize_for_non_string_raises() -> None:
    with pytest.raises(ConfigError):
        parse_optimize_for(123, "test")


def test_load_config_handles_type_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(
        loader_module, "_read_toml", lambda _path: (_ for _ in ()).throw(TypeError("boom"))
    )
    with pytest.raises(ConfigError):
        loader_module.load_config()


def test_get_config_wraps_load_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        loader_module, "load_config", lambda: (_ for _ in ()).throw(ConfigError("test", "boom"))
    )
    loader_module.get_config.cache_clear()
    with pytest.raises(ConfigError):
        loader_module.get_config()


def test_load_config_environment_override_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("FASTEST_ROUTE_ENV", "prod")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "prod-key")
    config = load_config()
    assert config.environment == "prod"


def test_load_config_log_level_override_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("FASTEST_ROUTE_LOG_LEVEL", "DEBUG")
    config = load_config()
    assert config.logging.level == "DEBUG"


def test_load_config_prod_requires_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("FASTEST_ROUTE_ENV", "prod")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_config()


def test_load_config_traffic_aware_invalid_departure_time_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.toml"
    _write_config(config_path)
    content = config_path.read_text()
    content = content.replace(
        '[google_maps]\napi_key = ""',
        '[google_maps]\napi_key = ""\ntraffic_aware_time = true\ndeparture_time = "soon"',
    )
    config_path.write_text(content)
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", str(config_path))
    with pytest.raises(ConfigError):
        load_config()


def test_load_config_missing_config_file_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FASTEST_ROUTE_CONFIG_PATH", "/tmp/does-not-exist-fastest-route.toml")
    with pytest.raises(ConfigError):
        load_config()
