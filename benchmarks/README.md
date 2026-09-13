# Benchmarks

The benchmark suite exercises the deterministic TSP solver hot path with
`pytest-benchmark`.

- `make bench` runs the benchmark with the repository-managed Python environment.
- Measurements are written to `artifacts/benchmark.json` by default. Set
  `BENCHMARK_JSON_PATH` to preserve results under another name.
- `make check` and CI execute the same benchmark script as a smoke gate and CI uploads
  the JSON result for inspection.
- Wall-clock results from different machines are not used as a merge-blocking comparison.
  Compare base and candidate revisions only on the same host and toolchain.

The measurement and review policy is documented in
`docs/performance/benchmark-governance.md`.
