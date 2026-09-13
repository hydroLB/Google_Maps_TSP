# Runbook: Benchmark Regression

## Scope

Use this runbook when the benchmark harness fails or controlled measurements show a
meaningful hot-path slowdown.

## Trigger Signals

- CI `Benchmark smoke` fails.
- Local `make bench` fails.
- Repeated base/candidate measurements on the same host show a material slowdown.

## Immediate Actions

1. Reproduce locally:
   - `make bench`
2. Capture profile data:
   - `make profile`
3. Confirm the base and candidate measurements use the same host, pinned Python,
   dependency set, and power/load conditions.

## Debugging Steps

1. Identify changed call path in benchmarked function.
2. Check for:
   - Added allocations or repeated conversions in hot loops.
   - New retries/IO in previously pure compute path.
   - Logging/debug statements in tight loops.
3. Preserve separate base and candidate JSON results with `BENCHMARK_JSON_PATH` and
   compare repeated runs.
4. Validate that non-performance changes did not alter benchmark setup.

## Mitigations

1. Rework hot loop logic to reduce per-iteration overhead.
2. Move invariant computations outside loops.
3. Replace repeated object creation with reused structures when safe.
4. If algorithm quality tradeoff is acceptable, tune config knobs with tests.

## Rollback Procedure

1. Revert performance-regressing commit(s) to last known-good.
2. Re-run:
   - `make bench`
   - `make check`
3. Merge rollback if regression remains unresolved and blocks delivery.

## Exit Criteria

- The benchmark smoke gate passes.
- Same-host measurements show the slowdown is fixed or explicitly accepted.
- Root cause and fix (or accepted tradeoff) are documented in PR notes.
