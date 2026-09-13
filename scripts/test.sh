#!/usr/bin/env bash
set -euo pipefail

py="$(./scripts/bootstrap_venv.sh)"
artifacts_dir="${CI_ARTIFACTS_DIR:-artifacts}"
critical_modules_coverage_min="${CRITICAL_MODULES_COVERAGE_MIN:-90}"

mkdir -p "${artifacts_dir}"

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "${py}" -m pytest \
  -p pytest_cov \
  -p pytest_benchmark.plugin \
  --junitxml="${artifacts_dir}/pytest-junit.xml" \
  --cov-report="xml:${artifacts_dir}/coverage.xml"

"${py}" -m coverage report \
  --include="TSP_GOOGLE_MAPS/fastest_route/config/loader.py,TSP_GOOGLE_MAPS/fastest_route/core/routing/routing_service.py,TSP_GOOGLE_MAPS/fastest_route/infrastructure/google_maps/client.py" \
  --fail-under="${critical_modules_coverage_min}" \
  > "${artifacts_dir}/critical-modules-coverage.txt"
