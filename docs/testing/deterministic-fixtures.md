# Deterministic Fixture Strategy

This repository keeps the existing test split:

- `tests/unit`: pure logic and narrow module behavior.
- `tests/integration`: IO boundaries with controlled doubles.
- `tests/e2e`: a service-level routing smoke through a fake Google Maps HTTP boundary. It does not
  open or drive the Tk GUI.

## Goals

- Every run produces the same result for the same commit.
- Fixtures never depend on external state, wall clock drift, or random values.
- Test failures point to a single behavior regression, not test-order effects.

## Fixture Rules

1. Use `tests/conftest.py::app_config` for shared defaults, or construct the relevant validated
   schema directly when a test needs a focused configuration variant.
2. Use `tmp_path` for all file-backed cache and output tests.
3. Inject a fake HTTP session/client at the integration boundary. Do not patch global networking
   when an existing constructor seam is available, and never call live Google APIs in CI.
4. Keep retry and timeout values low in tests through fixture config so failures are fast and deterministic.
5. Avoid global mutable fixtures. Prefer function-scoped fixtures unless there is a measured runtime need.

## Determinism Controls

- Randomness: do not use unseeded random inputs. Use explicit literals or seeded generators.
- Time: patch monotonic/time functions when asserting timeout paths.
- Environment: set/clear environment variables per test using `monkeypatch`.
- Filesystem: isolate with `tmp_path`; never write to project source paths.

## Coverage Focus

The configured aggregate branch-coverage threshold remains enforced via pytest configuration for
`fastest_route` except `fastest_route.presentation`, which is explicitly omitted. Targeted unit
tests still cover pure presentation helpers and controller/flow behavior, but those lines do not
contribute to the advertised aggregate percentage.

Critical-module coverage is additionally enforced in `scripts/test.sh` for:

- `TSP_GOOGLE_MAPS/fastest_route/config/loader.py`
- `TSP_GOOGLE_MAPS/fastest_route/core/routing/routing_service.py`
- `TSP_GOOGLE_MAPS/fastest_route/infrastructure/google_maps/client.py`

The default minimum is `90%` and is tunable with `CRITICAL_MODULES_COVERAGE_MIN`.

Real Tk widget creation, focus behavior, and native rendering require a desktop session. They are
manual checks today, not automated E2E or CI coverage; native Windows GUI behavior is unverified.
