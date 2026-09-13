#!/usr/bin/env bash
set -euo pipefail

py="$(./scripts/bootstrap_venv.sh)"

"${py}" -m ruff format --check TSP_GOOGLE_MAPS tests scripts/*.py
"${py}" -m ruff check TSP_GOOGLE_MAPS tests scripts/*.py
"${py}" -m mypy --config-file pyproject.toml
"${py}" -m bandit -q -r TSP_GOOGLE_MAPS
"${py}" -m pip_audit --strict --require-hashes --disable-pip -r requirements.lock
"${py}" -m pip_audit --strict --require-hashes --disable-pip -r requirements-dev.lock
./scripts/lockfile_hygiene.sh
./scripts/repo_hygiene.sh
./scripts/test.sh
"${py}" -m build --no-isolation
./scripts/bench.sh
