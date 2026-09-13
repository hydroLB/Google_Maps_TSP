# ADR 0002: Route via Core Ports and Infrastructure Adapters

## Status

Accepted

## Date

2026-02-20

## Context

Routing orchestration originally depended directly on infrastructure details
(Google Maps client and cache internals). That coupling made core harder to test
and constrained infrastructure changes.

## Decision

Define and consume core-owned ports:

- `RouteMatrixPort`
- `RouteCachePort`

Implement these ports in infrastructure adapters under
`fastest_route.infrastructure.adapters.routing_ports` and wire them at startup.

Contract tests (`tests/integration/test_routing_ports_contract.py`) verify adapter
conformance and delegation behavior.

## Consequences

Positive:

- Core orchestration is infrastructure-agnostic.
- Interface-level tests are stable and targeted.
- Infrastructure implementations can evolve independently.

Negative:

- Extra adapter layer and wiring code.
- Requires disciplined ownership of port contracts.

## Alternatives Considered

1. Keep direct infrastructure dependencies in core.
2. Use typing-only protocols in core without explicit adapter boundary module.

Both were rejected because they do not provide a clear, enforced boundary with
contract-level verification.
