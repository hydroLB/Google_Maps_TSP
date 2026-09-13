# Public API Surface Audit

## Scope

This audit documents the intentionally supported Python import surfaces for
`fastest_route` package consumers and internal module boundaries.

## Stable Public Exports

### `fastest_route.config`

- `get_config`
- `load_config`
- `AppConfig`
- `CacheConfig`
- `GoogleMapsConfig`
- `HttpConfig`
- `LoggingConfig`
- `RateLimitConfig`
- `RoutingConfig`
- `UiConfig`

### `fastest_route.core`

- `TspSolver`
- `RouteMatrixPort`
- `RouteCachePort`
- `RoutingService`

### `fastest_route.infrastructure`

- `build_routing_ports`
- `GoogleMapsClient`
- `RateLimiter`
- `RetryPolicy`

### `fastest_route.presentation`

- `RouteApp`

### `fastest_route.shared`

- `AppError`, `CacheError`, `CancellationError`, `ConfigError`,
  `ExternalServiceError`, `RateLimitError`, `ValidationError`
- `CancellationToken`
- `OptimizeFor`, `RouteRequest`, `RouteResult`, `TravelMode`

## Non-Public/Internal Modules

All modules not exported through package `__init__.py` files should be treated as
internal implementation details and may change without compatibility guarantees.

## Audit Outcome

- Package `__init__.py` files define explicit `__all__` for primary layers.
- No additional accidental top-level exports were introduced.
- Public API surface is documented and consistent with current package exports.
