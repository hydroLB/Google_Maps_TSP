# Configuration Reference

## Scope

This document is the central reference for all runtime tunables, defaults, constraints, and
environment layering behavior for this repository.

Source of truth in code:

- Loader: `TSP_GOOGLE_MAPS/fastest_route/config/loader.py`
- Section builders: `TSP_GOOGLE_MAPS/fastest_route/config/loading/sections/*.py`
- Validation schema: `TSP_GOOGLE_MAPS/fastest_route/config/schema/*.py`

Default runtime file:

- `TSP_GOOGLE_MAPS/config.toml` in a source checkout
- packaged `fastest_route/config/default.toml` after wheel installation

## Environment Layering Rules

Precedence order is deterministic:

1. Non-empty process environment variables (highest)
2. Supported values from the stable credential `.env`, only when the process variable is unset
3. Values from the config file selected by the process-only `FASTEST_ROUTE_CONFIG_PATH` override
4. Loader defaults from section builders (lowest)

Current environment overrides:

- `FASTEST_ROUTE_CONFIG_PATH`: Config file path override.
- `FASTEST_ROUTE_ENV`: Overrides `[app].environment`.
- `FASTEST_ROUTE_LOG_LEVEL`: Overrides `[logging].level`.
- `GOOGLE_MAPS_API_KEY`: Overrides `[google_maps].api_key`.

Behavior details:

- A source checkout reads the repository-root `.env`. An installed wheel reads
  `$XDG_CONFIG_HOME/fastest_route/.env`, falling back to `~/.config/fastest_route/.env` when
  `XDG_CONFIG_HOME` is unset. Launching from another working directory does not change that path.
- If `FASTEST_ROUTE_CONFIG_PATH` is unset, the source launcher uses
  `TSP_GOOGLE_MAPS/config.toml`; an installed wheel uses its packaged defaults.
- Executable entry points parse `.env` as data, never execute it as shell code, and accept only
  `GOOGLE_MAPS_API_KEY`, `FASTEST_ROUTE_ENV`, and `FASTEST_ROUTE_LOG_LEVEL`. The config-path
  override is process-only, so a credential file cannot replace trusted provider endpoints.
- `.env` is a plaintext credential file. Keep it user-private (`chmod 600` on POSIX); the GUI's
  persistence path creates parent directories and writes the file atomically.
- Empty env values are treated as unset for `FASTEST_ROUTE_ENV`, `FASTEST_ROUTE_LOG_LEVEL`,
  and `GOOGLE_MAPS_API_KEY`.
- Validation runs after all layering has been applied.

## Startup Validation Guarantees

Validation is fail-fast and happens before service wiring:

1. `fastest_route.entrypoint` loads the launch-mode-specific optional `.env` described above and
   calls `get_config()`; `TSP_GOOGLE_MAPS/main.py` is a compatibility launcher.
2. `load_config()` parses TOML and applies environment layering.
3. `AppConfig.validate()` validates every config section.
4. On failure, `ConfigError` is raised and startup exits non-zero.

Guarantees:

- Invalid config never proceeds to network client creation or GUI startup.
- Errors are location-tagged (`ConfigError`) and mapped at boundaries.
- Production-like environments require an API key; local/dev/test allow runtime key prompt.

## Tunables

### `[app]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `environment` | `str` | `"dev"` | must be non-empty | `FASTEST_ROUTE_ENV` |

### `[google_maps]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `api_key` | `str` | `""` | required when `environment` not in `{test, ci, dev, local}` | `GOOGLE_MAPS_API_KEY` |
| `distance_matrix_url` | `str` | Google Distance Matrix endpoint | HTTPS URL on `maps.googleapis.com` | None |
| `geocode_url` | `str` | Google Geocode endpoint | HTTPS URL on `maps.googleapis.com` | None |
| `places_autocomplete_url` | `str` | Google Places Autocomplete endpoint | HTTPS URL on `maps.googleapis.com` | None |
| `traffic_aware_time` | `bool` | `false` | boolean | None |
| `departure_time` | `str` | `"now"` | required when `traffic_aware_time=true`; must be `"now"` or non-negative unix seconds | None |
| `traffic_model` | `TrafficModel` | `"best_guess"` | one of `best_guess`, `optimistic`, `pessimistic` | None |

### `[cache]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `disk_path` | `path` | `~/.cache/fastest_route/distance_cache.json` | non-empty | None |
| `geocode_disk_path` | `path \| empty` | `""` (disabled) | when set: non-empty path | None |
| `route_cache_size` | `int` | `200` | `> 0` | None |
| `disk_cache_ttl_seconds` | `int` | `86400` | `> 0` | None |
| `geocode_cache_size` | `int` | `500` | `> 0` | None |
| `geocode_disk_cache_ttl_seconds` | `int` | `86400` | `> 0` | None |

Autocomplete predictions are held only for the active query and are not retained in the general
cache store. When traffic-aware driving uses `departure_time="now"`, cache identities rotate in
five-minute buckets; older bucket entries remain until `disk_cache_ttl_seconds` expires.

### `[routing]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `max_exact` | `int` | `7` | `> 1` | None |
| `two_opt_max_passes` | `int` | `8` | `> 0` | None |
| `nearest_neighbor_start_index` | `int` | `0` | `>= 0` | None |
| `default_mode` | `TravelMode` | `"driving"` | one of supported travel modes | None |
| `default_optimize_for` | `OptimizeFor` | `"time"` | one of supported metrics | None |
| `max_compute_seconds` | `float` | `60.0` | `> 0` | None |

### `[http]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `timeout_seconds` | `float` | `10.0` | `> 0` | None |
| `retry_max_attempts` | `int` | `3` | `> 0` | None |
| `retry_base_delay_seconds` | `float` | `0.4` | `> 0` | None |
| `retry_max_delay_seconds` | `float` | `6.0` | `> 0` | None |
| `retry_jitter_ratio` | `float` | `0.2` | `0 <= x <= 1` | None |
| `retry_statuses` | `list[int]` | `[429, 500, 502, 503, 504]` | list of integers | None |

### `[rate_limit]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `requests_per_second` | `float` | `5.0` | `> 0` | None |
| `burst` | `int` | `10` | `> 0` | None |
| `max_wait_seconds` | `float` | `10.0` | `> 0` | None |

### `[logging]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `level` | `str` | `"INFO"` | non-empty | `FASTEST_ROUTE_LOG_LEVEL` |

### `[ui]`

| Key | Type | Default | Constraints | Env override |
|---|---|---|---|---|
| `min_stops` | `int` | `3` | `> 0` | None |
| `max_stops` | `int` | `7` | `>= min_stops` and `<= 8` so two optional endpoints remain within the 100-element matrix bound | None |
| `autocomplete_min_chars` | `int` | `3` | `> 0` | None |
| `autocomplete_delay_ms` | `int` | `300` | `> 0` | None |
| `status_delay_ms` | `int` | `600` | `> 0` | None |
| `theme_mode` | `str` | `"auto"` | one of `auto`, `system`, `light`, `dark` | None |
| `os_theme_poll_seconds` | `float` | `2.0` | `0.5 <= x <= 60` | None |
