#!/usr/bin/env bash
set -euo pipefail

py="$(./scripts/bootstrap_venv.sh)"

"${py}" -m build --no-isolation
