# Benchmark Governance Policy

## Scope

This policy governs repeatable measurement of benchmarked hot paths without treating
wall-clock results from unrelated machines as directly comparable.

## Benchmarked Hot Path

Current benchmark target:

- `tests/benchmarks/test_routing_benchmark.py::test_tsp_solver_benchmark`

The canonical command is:

- `make bench`

It writes machine-readable output to `artifacts/benchmark.json` by default. Override the
destination with `BENCHMARK_JSON_PATH` when preserving multiple runs.

## Merge Gate

- Local `make check` and CI both execute `scripts/bench.sh`.
- The gate fails when the benchmark cannot execute successfully.
- CI uploads the JSON measurement so reviewers can inspect results and retain evidence.
- CI does not fail on a percentage comparison against a committed wall-clock baseline.

GitHub-hosted runners vary by CPU, virtualization, load, operating system, and Python
patch release. A numeric threshold against a result captured on another host creates
false regressions and false confidence.

## Comparative Review

When a change may affect solver performance:

1. Measure the base revision and candidate revision on the same host.
2. Use the same Python executable, dependency lockfiles, power mode, and background-load
   conditions for both revisions.
3. Preserve results separately, for example:
   - `BENCHMARK_JSON_PATH=artifacts/benchmark-base.json make bench`
   - `BENCHMARK_JSON_PATH=artifacts/benchmark-candidate.json make bench`
4. Repeat noisy measurements and compare the distribution, not a single fastest run.
5. Include the observed effect and its product impact in the PR when the difference is
   material.

`make bench-compare` remains a compatibility alias for `make bench`; it intentionally
does not compare against a cross-machine committed baseline.

## Enforcement Points

- Local: `make bench` and `make check`.
- CI: `Benchmark smoke` in `.github/workflows/ci.yml`.
- Required-check policy: `docs/ci/required-checks.md`.

## Incident Handling

When the benchmark cannot run, or controlled same-host measurements indicate a material
slowdown, follow:

- `docs/runbooks/performance-regression.md`
