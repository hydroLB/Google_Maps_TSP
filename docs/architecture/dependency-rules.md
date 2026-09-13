# Dependency Direction Rules

## Enforced Rules

Layer rules are enforced for imports under `TSP_GOOGLE_MAPS/fastest_route/**`.

- `shared` can import only `shared`.
- `observability` can import `observability`, `shared`.
- `config` can import `config`, `shared`.
- `core` can import `core`, `config`, `observability`, `shared`.
- `infrastructure` can import `infrastructure`, `config`, `observability`, `shared`.
- `presentation` can import `presentation`, `core`, `config`, `infrastructure`, `observability`, `shared`.

These rules apply to both absolute imports (`fastest_route.*`) and relative imports.

## Enforcement

- Guard script: `scripts/repo_hygiene.sh`
- Guard function: `check_layer_dependency_rules`
- Triggered by:
  - `make lint`
  - `make check`
  - CI `quality` job (`Repo hygiene guard`)

This is a hard-fail check and prevents new cross-layer coupling regressions.

## Routing Interface Boundary

Routing orchestration depends on core-owned ports instead of infrastructure concrete types:

- `fastest_route.core.ports.RouteMatrixPort`
- `fastest_route.core.ports.RouteCachePort`

Current adapter boundary:

- `fastest_route.infrastructure.adapters.routing_ports.build_routing_ports`
  maps infrastructure dependencies to core ports.
- `fastest_route.infrastructure.adapters.routing_ports.GoogleMapsRouteMatrixAdapter`
  implements `RouteMatrixPort` by delegating to `GoogleMapsClient`.
- `fastest_route.infrastructure.adapters.routing_ports.CacheStoreRouteCacheAdapter`
  implements `RouteCachePort` by delegating to `CacheStore`.

This keeps core orchestration stable while infrastructure implementations evolve independently.

Contract coverage:

- `tests/integration/test_routing_ports_contract.py` verifies adapter conformance and delegation for both ports.
