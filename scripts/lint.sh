#!/usr/bin/env bash
set -euo pipefail

py="$(./scripts/bootstrap_venv.sh)"

"${py}" -m ruff check TSP_GOOGLE_MAPS tests scripts/*.py
"${py}" -m mypy --config-file pyproject.toml
"${py}" -m bandit -q -r TSP_GOOGLE_MAPS
./scripts/lockfile_hygiene.sh
./scripts/repo_hygiene.sh
