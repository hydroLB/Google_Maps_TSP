#!/usr/bin/env bash
set -euo pipefail

die() {
  local location="${1:-scripts/lockfile_hygiene.sh.die}"
  local message="${2:-Unknown error}"
  printf '[ERROR] %s: %s\n' "${location}" "${message}" >&2
  exit 1
}

repo_root() {
  local location="scripts/lockfile_hygiene.sh.repo_root"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)" \
    || die "${location}" "Failed to resolve script directory."
  (cd "${script_dir}/.." >/dev/null 2>&1 && pwd) \
    || die "${location}" "Failed to resolve repository root."
}

resolve_python() {
  local location="scripts/lockfile_hygiene.sh.resolve_python"
  local root
  root="$(repo_root)"

  if [[ -n "${FASTEST_ROUTE_PYTHON:-}" ]]; then
    [[ -x "${FASTEST_ROUTE_PYTHON}" ]] \
      || die "${location}" "FASTEST_ROUTE_PYTHON is set but not executable: ${FASTEST_ROUTE_PYTHON}"
    printf '%s' "${FASTEST_ROUTE_PYTHON}"
    return 0
  fi

  if [[ -x "${root}/.venv/bin/python" ]]; then
    printf '%s' "${root}/.venv/bin/python"
    return 0
  fi

  if command -v python3.11 >/dev/null 2>&1; then
    printf '%s' "python3.11"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "python3"
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    printf '%s' "python"
    return 0
  fi

  die "${location}" "No Python interpreter found. Install Python 3.11.x and retry."
}

LOCKFILE_PYTHON=""

require_files_exist() {
  local location="scripts/lockfile_hygiene.sh.require_files_exist"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local required
  for required in requirements.txt requirements.lock requirements-dev.txt requirements-dev.lock; do
    [[ -f "${root}/${required}" ]] || die "${location}" "Missing required file: ${required}"
  done
}

check_lockfile_covers_direct_requirements() {
  local location="scripts/lockfile_hygiene.sh.check_lockfile_covers_direct_requirements"
  local root="${1:-}"
  local source_file="${2:-}"
  local lockfile="${3:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."
  [[ -n "${source_file}" ]] || die "${location}" "Missing source file argument."
  [[ -n "${lockfile}" ]] || die "${location}" "Missing lockfile argument."

  if ! "${LOCKFILE_PYTHON}" - "${root}/${source_file}" "${root}/${lockfile}" <<'PY'
from __future__ import annotations

import pathlib
import re
import sys

source_path = pathlib.Path(sys.argv[1])
lock_path = pathlib.Path(sys.argv[2])
requirement_pattern = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s;\\]+)"
)


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path: pathlib.Path, *, allow_includes: bool) -> dict[str, str]:
    found: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#") or (allow_includes and line.startswith("-r ")):
            continue
        if line.startswith("--hash="):
            continue
        match = requirement_pattern.match(line)
        if match is None:
            print(f"{path.name}:{line_number}: unsupported requirement: {raw_line}")
            raise SystemExit(1)
        found[normalized(match.group(1))] = match.group(2)
    return found


direct = pins(source_path, allow_includes=True)
locked = pins(lock_path, allow_includes=False)
drift = [
    f"{name}=={version} (locked: {locked.get(name, 'missing')})"
    for name, version in sorted(direct.items())
    if locked.get(name) != version
]
if drift:
    print(f"Direct dependency drift between {source_path.name} and {lock_path.name}:")
    for item in drift:
        print(f"- {item}")
    raise SystemExit(1)
PY
  then
    die "${location}" "Direct requirements and generated lockfile are out of sync."
  fi
}

check_lockfile_is_fully_pinned() {
  local location="scripts/lockfile_hygiene.sh.check_lockfile_is_fully_pinned"
  local root="${1:-}"
  local lockfile="${2:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."
  [[ -n "${lockfile}" ]] || die "${location}" "Missing lockfile argument."

  if ! "${LOCKFILE_PYTHON}" - "${root}/${lockfile}" <<'PY'
from __future__ import annotations

import pathlib
import sys

path = pathlib.Path(sys.argv[1])
bad_lines: list[tuple[int, str]] = []
for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("-"):
        continue
    if "==" not in line:
        bad_lines.append((line_number, raw_line))
if bad_lines:
    for line_number, raw_line in bad_lines:
        print(f"{path.name}:{line_number}: {raw_line}")
    raise SystemExit(1)
PY
  then
    die "${location}" "Lockfile contains non-pinned dependency entries: ${lockfile}"
  fi
}

check_lockfile_has_hashes() {
  local location="scripts/lockfile_hygiene.sh.check_lockfile_has_hashes"
  local root="${1:-}"
  local lockfile="${2:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."
  [[ -n "${lockfile}" ]] || die "${location}" "Missing lockfile argument."

  if ! "${LOCKFILE_PYTHON}" - "${root}/${lockfile}" <<'PY'
from __future__ import annotations

import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
requirement_pattern = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[^]]+\])?==")
missing: list[tuple[int, str]] = []
for index, raw_line in enumerate(lines):
    line = raw_line.strip()
    if requirement_pattern.match(line) is None:
        continue
    cursor = index
    has_hash = False
    while cursor < len(lines):
        candidate = lines[cursor].strip()
        if cursor > index and requirement_pattern.match(candidate):
            break
        if "--hash=sha256:" in candidate:
            has_hash = True
        cursor += 1
    if not has_hash:
        missing.append((index + 1, raw_line))
if missing:
    for line_number, raw_line in missing:
        print(f"{path.name}:{line_number}: missing sha256 hash: {raw_line}")
    raise SystemExit(1)
PY
  then
    die "${location}" "Lockfile contains unhashed distributions: ${lockfile}"
  fi
}

check_runtime_lock_is_dev_subset() {
  local location="scripts/lockfile_hygiene.sh.check_runtime_lock_is_dev_subset"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  if ! "${LOCKFILE_PYTHON}" - "${root}/requirements.lock" "${root}/requirements-dev.lock" <<'PY'
from __future__ import annotations

import pathlib
import re
import sys

requirement_pattern = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s\\]+)")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = requirement_pattern.match(raw_line.strip())
        if match is not None:
            result[normalized(match.group(1))] = match.group(2)
    return result


runtime = pins(pathlib.Path(sys.argv[1]))
development = pins(pathlib.Path(sys.argv[2]))
drift = [
    f"{name}=={version} (development lock: {development.get(name, 'missing')})"
    for name, version in sorted(runtime.items())
    if development.get(name) != version
]
if drift:
    print("Runtime lock is not an identical subset of requirements-dev.lock:")
    for item in drift:
        print(f"- {item}")
    raise SystemExit(1)
PY
  then
    die "${location}" "Runtime and development locks have transitive dependency drift."
  fi
}

main() {
  local root
  root="$(repo_root)"
  LOCKFILE_PYTHON="$(resolve_python)"
  require_files_exist "${root}"
  check_lockfile_covers_direct_requirements "${root}" "requirements.txt" "requirements.lock"
  check_lockfile_covers_direct_requirements "${root}" "requirements-dev.txt" "requirements-dev.lock"
  check_lockfile_is_fully_pinned "${root}" "requirements.lock"
  check_lockfile_is_fully_pinned "${root}" "requirements-dev.lock"
  check_lockfile_has_hashes "${root}" "requirements.lock"
  check_lockfile_has_hashes "${root}" "requirements-dev.lock"
  check_runtime_lock_is_dev_subset "${root}"
}

main "$@"
