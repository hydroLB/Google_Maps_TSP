#!/usr/bin/env bash
set -euo pipefail

py="$(./scripts/bootstrap_venv.sh)"

"${py}" -m ruff format TSP_GOOGLE_MAPS tests scripts/*.py
"${py}" -m ruff check --fix TSP_GOOGLE_MAPS tests scripts/*.py
