# ADR 0001: Enforce Layer Dependency Direction

## Status

Accepted

## Date

2026-02-20

## Context

The repository has grown into multiple layers (`shared`, `observability`, `config`,
`core`, `infrastructure`, `presentation`). Without enforcement, direct imports across
layers can create hidden coupling and make changes risky.

## Decision

Enforce explicit import direction rules in CI and local checks using
`scripts/repo_hygiene.sh` (`check_layer_dependency_rules`).

Current rules:

- `shared` imports only `shared`.
- `observability` imports `observability`, `shared`.
- `config` imports `config`, `shared`.
- `core` imports `core`, `config`, `observability`, `shared`.
- `infrastructure` imports `infrastructure`, `config`, `observability`, `shared`.
- `presentation` imports `presentation`, `core`, `config`, `infrastructure`,
  `observability`, `shared`.

## Consequences

Positive:

- Prevents new cross-layer coupling regressions.
- Keeps business logic isolated in core.
- Improves review clarity and maintainability.

Negative:

- Some refactors require adapter extraction before moving code.
- Guard rules must be updated when architecture intentionally changes.

## Alternatives Considered

1. Convention-only guidelines without enforcement.
2. Per-module manual review of import direction.

Both were rejected due to drift risk and review overhead.
