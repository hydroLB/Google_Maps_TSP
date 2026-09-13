#!/usr/bin/env bash
set -euo pipefail

py="$(./scripts/bootstrap_venv.sh)"
artifacts_dir="${CI_ARTIFACTS_DIR:-artifacts}"
benchmark_json="${BENCHMARK_JSON_PATH:-${artifacts_dir}/benchmark.json}"

mkdir -p "$(dirname "${benchmark_json}")"

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "${py}" -m pytest \
  -p pytest_benchmark.plugin \
  -o addopts= \
  --benchmark-enable \
  --benchmark-only \
  --benchmark-json="${benchmark_json}" \
  tests/benchmarks/test_routing_benchmark.py

printf 'Benchmark measurements written to %s\n' "${benchmark_json}"
