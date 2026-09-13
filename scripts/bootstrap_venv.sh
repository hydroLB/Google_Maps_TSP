#!/usr/bin/env bash
set -euo pipefail

log() {
  local level="${1:-INFO}"
  local message="${2:-}"
  printf '[%s] %s\n' "${level}" "${message}" >&2
}

die() {
  local location="${1:-scripts/bootstrap_venv.sh.die}"
  local message="${2:-Unknown error}"
  log "ERROR" "${location}: ${message}"
  exit 1
}

repo_root() {
  local location="scripts/bootstrap_venv.sh.repo_root"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)" \
    || die "${location}" "Failed to resolve script directory."
  (cd "${script_dir}/.." >/dev/null 2>&1 && pwd) \
    || die "${location}" "Failed to resolve repository root."
}

resolve_python() {
  local location="scripts/bootstrap_venv.sh.resolve_python"
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

  die "${location}" "No Python interpreter found. Install Python 3.11+ and retry."
}

ensure_python_version() {
  local location="scripts/bootstrap_venv.sh.ensure_python_version"
  local py="${1:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing interpreter argument."
  "${py}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,11) else 1)' \
    || die "${location}" "Python must be 3.11.x. Detected: $(${py} --version 2>&1 | tr -d '\n')"
}

ensure_venv() {
  local location="scripts/bootstrap_venv.sh.ensure_venv"
  local root
  root="$(repo_root)"
  local venv_python="${root}/.venv/bin/python"
  if [[ -x "${venv_python}" ]]; then
    if "${venv_python}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,11) else 1)'; then
      printf '%s' "${venv_python}"
      return 0
    fi
    log "WARN" "Existing .venv is not Python 3.11.x. Recreating pinned environment."
    rm -rf "${root}/.venv"
  fi

  local base_python
  base_python="$(resolve_python)"
  ensure_python_version "${base_python}"
  log "INFO" "Creating virtual environment at ${root}/.venv"
  "${base_python}" -m venv "${root}/.venv" \
    || die "${location}" "Failed to create virtual environment."
  [[ -x "${venv_python}" ]] || die "${location}" "Virtual environment is missing python executable."
  printf '%s' "${venv_python}"
}

requirements_lockfiles() {
  local location="scripts/bootstrap_venv.sh.requirements_lockfiles"
  local root
  root="$(repo_root)"

  local dev_lock="${root}/requirements-dev.lock"
  [[ -f "${dev_lock}" ]] || die "${location}" "Missing requirements-dev.lock."
  printf '%s\n' "${dev_lock}"
}

run_lockfile_hygiene() {
  local location="scripts/bootstrap_venv.sh.run_lockfile_hygiene"
  local root
  root="$(repo_root)"
  local hygiene_script="${root}/scripts/lockfile_hygiene.sh"
  [[ -x "${hygiene_script}" ]] || die "${location}" "Missing executable lockfile hygiene script."
  "${hygiene_script}" || die "${location}" "Lockfile hygiene checks failed."
}

lockfile_hash() {
  local location="scripts/bootstrap_venv.sh.lockfile_hash"
  local py="${1:-}"
  local lockfile="${2:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing interpreter argument."
  [[ -n "${lockfile}" ]] || die "${location}" "Missing lockfile argument."
  "${py}" -c "import hashlib, pathlib, sys; p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest())" "${lockfile}" \
    || die "${location}" "Failed to hash lockfile: ${lockfile}"
}

ensure_deps_installed() {
  local location="scripts/bootstrap_venv.sh.ensure_deps_installed"
  local py="${1:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing interpreter argument."

  local root
  root="$(repo_root)"
  run_lockfile_hygiene
  local -a lockfiles=()
  local lockfile
  while IFS= read -r lockfile; do
    [[ -n "${lockfile}" ]] && lockfiles+=("${lockfile}")
  done < <(requirements_lockfiles)

  if ! "${py}" -m pip --version >/dev/null 2>&1; then
    log "WARN" "pip is not available in .venv. Repairing with ensurepip."
    "${py}" -m ensurepip --upgrade >&2 \
      || die "${location}" "Failed to repair pip with ensurepip."
  fi

  local needs_install="0"
  local marker_path current_hash stored_hash
  for lockfile in "${lockfiles[@]}"; do
    marker_path="${root}/.venv/.${lockfile##*/}.sha256"
    current_hash="$(lockfile_hash "${py}" "${lockfile}")"
    stored_hash=""
    if [[ -f "${marker_path}" ]]; then
      stored_hash="$(cat "${marker_path}" 2>/dev/null || true)"
    fi
    if [[ "${current_hash}" != "${stored_hash}" ]]; then
      needs_install="1"
      break
    fi
  done

  if [[ "${needs_install}" == "0" ]]; then
    return 0
  fi

  log "INFO" "Installing dependencies from the development lockfile"

  for lockfile in "${lockfiles[@]}"; do
    marker_path="${root}/.venv/.${lockfile##*/}.sha256"
    current_hash="$(lockfile_hash "${py}" "${lockfile}")"
    stored_hash=""
    if [[ -f "${marker_path}" ]]; then
      stored_hash="$(cat "${marker_path}" 2>/dev/null || true)"
    fi
    if [[ "${current_hash}" == "${stored_hash}" ]]; then
      continue
    fi
    log "INFO" "Installing ${lockfile##*/}"
    "${py}" -m pip install --require-hashes -r "${lockfile}" >&2 \
      || die "${location}" "Dependency installation failed for ${lockfile##*/}."
    printf '%s' "${current_hash}" >"${marker_path}" \
      || die "${location}" "Failed to write marker file ${marker_path}."
  done
}

ensure_pre_commit_hooks_installed() {
  local location="scripts/bootstrap_venv.sh.ensure_pre_commit_hooks_installed"
  local py="${1:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing interpreter argument."

  local root
  root="$(repo_root)"
  local config_path="${root}/.pre-commit-config.yaml"
  local hooks_path="${root}/.githooks"

  if [[ ! -f "${config_path}" || ! -d "${hooks_path}" ]]; then
    return 0
  fi

  if ! git -C "${root}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  log "INFO" "Configuring repository-managed git hooks"
  git -C "${root}" config core.hooksPath .githooks \
    || die "${location}" "Failed to set core.hooksPath to .githooks."
  "${py}" -m pre_commit install-hooks --config "${config_path}" >/dev/null \
    || die "${location}" "Failed to install pre-commit hook environments."
}

main() {
  local py
  py="$(ensure_venv)"
  ensure_deps_installed "${py}"
  ensure_pre_commit_hooks_installed "${py}"
  printf '%s\n' "${py}"
}

main "$@"
