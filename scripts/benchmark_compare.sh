#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' \
  'Cross-machine wall-clock comparison is intentionally disabled; running the canonical benchmark measurement instead.' \
  >&2
exec ./scripts/bench.sh
